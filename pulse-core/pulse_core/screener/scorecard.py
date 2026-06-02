"""Screener 评分卡模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Required, TypedDict

# 容差:同轴权重和、加权一致性校验(详见 docs/screener.md §5.3 规则 4-5)
WEIGHT_TOLERANCE: float = 1e-6


class RewardDim(TypedDict, total=False):
    """reward 轴单维度(JSONB §5.1)。

    必填:score / weight
    可选:details(snake_case keys)

    total=False 让所有 key 可选;运行时强校验由 Scorecard.validate() 负责。
    """

    score: Required[float]
    weight: Required[float]
    details: dict[str, Any]


class RiskDim(TypedDict, total=False):
    """risk 轴单维度(JSONB §5.1)。

    必填:score / weight / source
    可选:details

    source 格式:
    - "shared:<func_name>"  共享 risk 维度(实现在 dimensions/risk.py)
    - "strategy:<strategy_name>"  策略私有 risk 维度
    """

    score: Required[float]
    weight: Required[float]
    source: Required[str]
    details: dict[str, Any]


@dataclass
class Scorecard:
    """双轴评分卡。详见 docs/screener.md §5。

    - 由 Strategy.score() 通过 Scorecard.build() 构造
    - Runner 落库前调用 .validate() 校验 §5.3 全部强制规则,失败抛 ValueError
    - .to_jsonb() 返回 §5.1 形状的 dict,可直接写入 daily_picks.scorecard JSONB 列
    - DB 列 reward_score / risk_score / final_score 由 axis_scores 派生写入

    字段直接镜像 §5.1 JSONB 顶层 4 个 key。
    """

    axis_weights: dict[str, float]
    axis_scores: dict[str, float]
    reward_dimensions: dict[str, RewardDim]
    risk_dimensions: dict[str, RiskDim]

    @classmethod
    def build(
        cls,
        reward: dict[str, RewardDim],
        risk: dict[str, RiskDim],
        w_reward: float = 0.70,
        w_risk: float = 0.30,
    ) -> Scorecard:
        """从维度字典构造 Scorecard,自动派生 axis_scores。

        Args:
            reward: reward 轴维度字典 {dim_name: {"score", "weight", "details"?}}
            risk: risk 轴维度字典(必须含至少 1 个 source 以 "shared:" 开头的维度)
            w_reward: reward 轴在 final_score 中的权重(默认 0.70)
            w_risk: risk 轴在 final_score 中的权重(默认 0.30)

        派生计算(§4.1):
            reward_score = Σ(dim.score × dim.weight)  for dim in reward
            risk_score   = Σ(dim.score × dim.weight)  for dim in risk
            final_score  = w_reward × reward_score + w_risk × risk_score

        注意:本方法不调用 validate(),允许测试构造非法 Scorecard 验证校验逻辑。
              Runner 在落库前显式调用 validate()。
        """
        reward_score = sum(d["score"] * d["weight"] for d in reward.values())
        risk_score = sum(d["score"] * d["weight"] for d in risk.values())
        final_score = w_reward * reward_score + w_risk * risk_score

        return cls(
            axis_weights={"reward": w_reward, "risk": w_risk},
            axis_scores={
                "reward": round(reward_score, 2),
                "risk": round(risk_score, 2),
                "final": round(final_score, 2),
            },
            reward_dimensions=dict(reward),
            risk_dimensions=dict(risk),
        )

    def validate(self) -> None:
        """校验 §5.3 全部强制规则。失败抛 ValueError。"""
        if not self.reward_dimensions:
            raise ValueError(
                "Scorecard 规则 §5.3-2 违反:reward_dimensions 至少 1 个维度,实际 0"
            )
        if not self.risk_dimensions:
            raise ValueError(
                "Scorecard 规则 §5.3-2 违反:risk_dimensions 至少 1 个维度,实际 0"
            )

        shared_count = sum(
            1
            for d in self.risk_dimensions.values()
            if d.get("source", "").startswith("shared:")
        )
        if shared_count == 0:
            sources = [d.get("source", "<missing>") for d in self.risk_dimensions.values()]
            raise ValueError(
                "Scorecard 规则 §5.3-3 违反:risk_dimensions 至少需 1 个 "
                f"source 以 'shared:' 开头,实际 sources={sources}"
            )

        reward_weight_sum = sum(d["weight"] for d in self.reward_dimensions.values())
        if abs(reward_weight_sum - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-4 违反:reward 轴 Σ weight = "
                f"{reward_weight_sum},应为 1.0(容差 {WEIGHT_TOLERANCE})"
            )
        risk_weight_sum = sum(d["weight"] for d in self.risk_dimensions.values())
        if abs(risk_weight_sum - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-4 违反:risk 轴 Σ weight = "
                f"{risk_weight_sum},应为 1.0(容差 {WEIGHT_TOLERANCE})"
            )

        expected_reward = sum(
            d["score"] * d["weight"] for d in self.reward_dimensions.values()
        )
        expected_risk = sum(
            d["score"] * d["weight"] for d in self.risk_dimensions.values()
        )
        w_reward = self.axis_weights.get("reward")
        w_risk = self.axis_weights.get("risk")
        if w_reward is None or w_risk is None:
            raise ValueError(
                "Scorecard 规则 §5.3-1 违反:axis_weights 缺少 reward / risk 键,"
                f"实际 {self.axis_weights}"
            )
        expected_final = w_reward * expected_reward + w_risk * expected_risk

        actual_reward = self.axis_scores.get("reward")
        actual_risk = self.axis_scores.get("risk")
        actual_final = self.axis_scores.get("final")
        if actual_reward is None or actual_risk is None or actual_final is None:
            raise ValueError(
                "Scorecard 规则 §5.3-1 违反:axis_scores 缺少 reward/risk/final,"
                f"实际 {self.axis_scores}"
            )

        rounded_reward = round(expected_reward, 2)
        rounded_risk = round(expected_risk, 2)
        rounded_final = round(expected_final, 2)

        if abs(actual_reward - rounded_reward) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-5 违反:axis_scores.reward = "
                f"{actual_reward},现场加权和 = {rounded_reward}(容差 {WEIGHT_TOLERANCE})"
            )
        if abs(actual_risk - rounded_risk) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-5 违反:axis_scores.risk = "
                f"{actual_risk},现场加权和 = {rounded_risk}(容差 {WEIGHT_TOLERANCE})"
            )
        if abs(actual_final - rounded_final) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-5 违反:axis_scores.final = "
                f"{actual_final},现场加权和 = {rounded_final}(容差 {WEIGHT_TOLERANCE})"
            )

        for key in self.axis_weights:
            _assert_snake_case(key, f"axis_weights.{key}")
        for key in self.axis_scores:
            _assert_snake_case(key, f"axis_scores.{key}")
        for dim_name in self.reward_dimensions:
            _assert_snake_case(dim_name, f"reward_dimensions.{dim_name}")
        for dim_name in self.risk_dimensions:
            _assert_snake_case(dim_name, f"risk_dimensions.{dim_name}")

    def to_jsonb(self) -> dict[str, Any]:
        """序列化为 §5.1 形状的 dict,可直接写入 daily_picks.scorecard JSONB 列。"""
        return {
            "axis_weights": dict(self.axis_weights),
            "axis_scores": dict(self.axis_scores),
            "reward_dimensions": {k: dict(v) for k, v in self.reward_dimensions.items()},
            "risk_dimensions": {k: dict(v) for k, v in self.risk_dimensions.items()},
        }


def _assert_snake_case(value: str, path: str) -> None:
    """断言 value 是合法的 snake_case 标识符。失败抛 ValueError(规则 6)。"""
    if not value:
        raise ValueError(f"Scorecard 规则 §5.3-6 违反:{path} 为空")
    if not all(c.islower() or c.isdigit() or c == "_" for c in value):
        raise ValueError(
            f"Scorecard 规则 §5.3-6 违反:{path} = '{value}' 含非 snake_case 字符"
        )
    if value[0].isdigit():
        raise ValueError(
            f"Scorecard 规则 §5.3-6 违反:{path} = '{value}' 以数字开头"
        )
