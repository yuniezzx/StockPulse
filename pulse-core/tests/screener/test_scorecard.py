"""Scorecard.validate() 强制规则覆盖测试。详见 docs/screener.md §5.3。"""

from __future__ import annotations

import pytest

from pulse_core.screener.scorecard import RewardDim, RiskDim, Scorecard


def _valid_scorecard() -> Scorecard:
    return Scorecard.build(
        reward={
            "limit_up_strength": {"score": 88.0, "weight": 0.6},
            "sector_momentum":   {"score": 84.0, "weight": 0.4},
        },
        risk={
            "liquidity_risk": {
                "score": 85.0, "weight": 1.0,
                "source": "shared:liquidity_risk",
            },
        },
        w_reward=0.7, w_risk=0.3,
    )


class TestBuild:
    def test_axis_scores_derived_correctly(self) -> None:
        sc = _valid_scorecard()
        assert sc.axis_scores["reward"] == 86.4
        assert sc.axis_scores["risk"] == 85.0
        assert sc.axis_scores["final"] == 85.98

    def test_axis_weights_mirror_args(self) -> None:
        sc = _valid_scorecard()
        assert sc.axis_weights == {"reward": 0.7, "risk": 0.3}

    def test_dimensions_shallow_copied(self) -> None:
        reward: dict[str, RewardDim] = {"a": {"score": 80.0, "weight": 1.0}}
        risk: dict[str, RiskDim] = {
            "liquidity_risk": {
                "score": 80.0, "weight": 1.0, "source": "shared:liquidity_risk",
            },
        }
        sc = Scorecard.build(reward=reward, risk=risk)
        reward["evil"] = {"score": 0, "weight": 0}
        assert "evil" not in sc.reward_dimensions

    def test_to_jsonb_shape_matches_spec(self) -> None:
        sc = _valid_scorecard()
        jsonb = sc.to_jsonb()
        assert set(jsonb.keys()) == {
            "axis_weights", "axis_scores", "reward_dimensions", "risk_dimensions",
        }
        assert jsonb["risk_dimensions"]["liquidity_risk"]["source"] == "shared:liquidity_risk"


class TestValidatePass:
    def test_canonical_scorecard_passes(self) -> None:
        _valid_scorecard().validate()


class TestValidateRule2RewardEmpty:
    """规则 §5.3-2: reward_dimensions 至少 1 个维度。"""

    def test_empty_reward_raises(self) -> None:
        sc = _valid_scorecard()
        sc.reward_dimensions = {}
        with pytest.raises(ValueError, match="§5.3-2.*reward_dimensions"):
            sc.validate()


class TestValidateRule2RiskEmpty:
    """规则 §5.3-2: risk_dimensions 至少 1 个维度。"""

    def test_empty_risk_raises(self) -> None:
        sc = _valid_scorecard()
        sc.risk_dimensions = {}
        with pytest.raises(ValueError, match="§5.3-2.*risk_dimensions"):
            sc.validate()


class TestValidateRule3RiskNoShared:
    """规则 §5.3-3: risk 至少 1 个 source 以 'shared:' 开头。"""

    def test_only_strategy_source_raises(self) -> None:
        sc = Scorecard.build(
            reward={"a": {"score": 80.0, "weight": 1.0}},
            risk={
                "first_board_difficulty": {
                    "score": 80.0, "weight": 1.0,
                    "source": "strategy:limit_up_replay",
                },
            },
        )
        with pytest.raises(ValueError, match="§5.3-3.*shared:"):
            sc.validate()

    def test_missing_source_raises(self) -> None:
        sc = Scorecard.build(
            reward={"a": {"score": 80.0, "weight": 1.0}},
            risk={"foo": {"score": 80.0, "weight": 1.0}},  # type: ignore[typeddict-item]
        )
        with pytest.raises(ValueError, match="§5.3-3"):
            sc.validate()


class TestValidateRule4WeightSum:
    """规则 §5.3-4: 同轴 Σ weight ≈ 1.0(容差 1e-6)。"""

    def test_reward_weight_sum_below_tolerance_raises(self) -> None:
        sc = Scorecard.build(
            reward={
                "a": {"score": 80.0, "weight": 0.5},
                "b": {"score": 80.0, "weight": 0.49},  # sum = 0.99
            },
            risk={"liquidity_risk": {
                "score": 80.0, "weight": 1.0, "source": "shared:liquidity_risk",
            }},
        )
        with pytest.raises(ValueError, match="§5.3-4.*reward.*0.99"):
            sc.validate()

    def test_risk_weight_sum_above_tolerance_raises(self) -> None:
        sc = Scorecard.build(
            reward={"a": {"score": 80.0, "weight": 1.0}},
            risk={
                "liquidity_risk": {
                    "score": 80.0, "weight": 0.55, "source": "shared:liquidity_risk",
                },
                "vol_risk": {
                    "score": 80.0, "weight": 0.50, "source": "shared:vol",
                },  # sum = 1.05
            },
        )
        with pytest.raises(ValueError, match="§5.3-4.*risk.*1.05"):
            sc.validate()

    def test_weight_sum_within_tolerance_passes(self) -> None:
        sc = Scorecard.build(
            reward={
                "a": {"score": 80.0, "weight": 0.5 + 5e-7},
                "b": {"score": 80.0, "weight": 0.5 - 5e-7},
            },
            risk={"liquidity_risk": {
                "score": 80.0, "weight": 1.0, "source": "shared:liquidity_risk",
            }},
        )
        sc.validate()


class TestValidateRule5AxisScoresMismatch:
    """规则 §5.3-5: axis_scores 与现场加权和一致(容差 1e-6)。"""

    def test_tampered_reward_score_raises(self) -> None:
        sc = _valid_scorecard()
        sc.axis_scores["reward"] = 99.0
        with pytest.raises(ValueError, match="§5.3-5.*axis_scores.reward"):
            sc.validate()

    def test_tampered_risk_score_raises(self) -> None:
        sc = _valid_scorecard()
        sc.axis_scores["risk"] = 50.0
        with pytest.raises(ValueError, match="§5.3-5.*axis_scores.risk"):
            sc.validate()

    def test_tampered_final_score_raises(self) -> None:
        sc = _valid_scorecard()
        sc.axis_scores["final"] = 50.0
        with pytest.raises(ValueError, match="§5.3-5.*axis_scores.final"):
            sc.validate()


class TestValidateRule6SnakeCase:
    """规则 §5.3-6: JSONB 内部 key 全部 snake_case。"""

    def test_camel_case_dim_name_raises(self) -> None:
        sc = Scorecard.build(
            reward={"limitUpStrength": {"score": 80.0, "weight": 1.0}},  # camelCase
            risk={"liquidity_risk": {
                "score": 80.0, "weight": 1.0, "source": "shared:liquidity_risk",
            }},
        )
        with pytest.raises(ValueError, match="§5.3-6.*limitUpStrength"):
            sc.validate()

    def test_dim_name_starts_with_digit_raises(self) -> None:
        sc = Scorecard.build(
            reward={"1st_dim": {"score": 80.0, "weight": 1.0}},
            risk={"liquidity_risk": {
                "score": 80.0, "weight": 1.0, "source": "shared:liquidity_risk",
            }},
        )
        with pytest.raises(ValueError, match="§5.3-6.*1st_dim"):
            sc.validate()
