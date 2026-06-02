from __future__ import annotations

from datetime import date

import pandas as pd

from pulse_core.screener.contracts import PickContext, ScreenerData
from pulse_core.screener.strategies.limit_up_replay import (
    LIMIT_UP_PCT,
    LimitUpReplayStrategy,
    _gaussian_score,
)


def _ctx(
    *,
    history_pct: list[float],
    history_close: list[float] | None = None,
    today_pct: float = 1.0,
    today_close: float = 10.0,
    today_vol: float = 2_000_000.0,
) -> PickContext:
    n = len(history_pct)
    closes = history_close or [10.0] * n
    history_rows = [
        {
            "ts_code":    "000001.SZ",
            "trade_date": pd.Timestamp("2026-05-01") + pd.Timedelta(days=i),
            "open":       10.0,
            "high":       11.0,
            "low":        9.0,
            "close":      closes[i],
            "vol":        1_500_000.0,
            "pct_chg":    history_pct[i],
            "amount":     500_000.0,
        }
        for i in range(n)
    ]
    if history_rows:
        history = pd.DataFrame(history_rows).set_index(["ts_code", "trade_date"])
        stock_history = history.xs("000001.SZ", level="ts_code")
    else:
        history = pd.DataFrame().set_index(
            pd.MultiIndex.from_tuples([], names=["ts_code", "trade_date"])
        )
        stock_history = pd.DataFrame()

    daily = pd.DataFrame(
        [{
            "ts_code": "000001.SZ",
            "close": today_close,
            "vol": today_vol,
            "pct_chg": today_pct,
            "amount": 800_000.0,
        }]
    ).set_index("ts_code")
    basic = pd.DataFrame(
        [{"ts_code": "000001.SZ", "turnover_rate": 2.5}]
    ).set_index("ts_code")

    empty = pd.DataFrame().set_index(pd.Index([], name="ts_code"))
    data = ScreenerData(
        daily=daily, basic=basic, moneyflow=empty,
        trend=empty, momentum=empty, volume=empty, moneyflow_ind=empty,
        history=history, stocks=empty,
        trade_date=date(2026, 5, 21), universe=["000001.SZ"],
    )

    return PickContext(
        ts_code="000001.SZ",
        trade_date=date(2026, 5, 21),
        daily=daily.loc["000001.SZ"],
        basic=basic.loc["000001.SZ"],
        moneyflow=None, trend=None, momentum=None, volume=None, moneyflow_ind=None,
        history=stock_history,
        data=data,
    )


class TestLimitUpReplayScore:
    def test_no_recent_limit_up_returns_none(self):
        ctx = _ctx(history_pct=[1.0] * 10)
        result = LimitUpReplayStrategy().score(ctx)
        assert result is None

    def test_today_is_limit_up_returns_none(self):
        ctx = _ctx(history_pct=[10.0, 1.0] + [1.0] * 8, today_pct=10.0)
        result = LimitUpReplayStrategy().score(ctx)
        assert result is None

    def test_empty_history_returns_none(self):
        ctx = _ctx(history_pct=[])
        result = LimitUpReplayStrategy().score(ctx)
        assert result is None

    def test_normal_path_returns_valid_scorecard(self):
        ctx = _ctx(
            history_pct=[10.0] + [1.0] * 9,
            history_close=[10.5] + [10.5] * 9,
            today_pct=1.0,
            today_close=10.0,
        )
        result = LimitUpReplayStrategy().score(ctx)
        assert result is not None
        result.validate()
        assert "recent_limit_up_strength" in result.reward_dimensions
        assert "volume_expansion" in result.reward_dimensions
        assert "pullback_quality" in result.reward_dimensions
        assert "liquidity_risk" in result.risk_dimensions
        assert result.risk_dimensions["liquidity_risk"]["source"] == "shared:liquidity_risk"

    def test_reward_weights_sum_to_one(self):
        ctx = _ctx(history_pct=[10.0] + [1.0] * 9)
        result = LimitUpReplayStrategy().score(ctx)
        assert result is not None
        total = sum(d["weight"] for d in result.reward_dimensions.values())
        assert abs(total - 1.0) < 1e-6

    def test_strength_score_proportional_to_count(self):
        ctx = _ctx(history_pct=[10.0, 10.0, 10.0] + [1.0] * 7)
        result = LimitUpReplayStrategy().score(ctx)
        assert result is not None
        assert result.reward_dimensions["recent_limit_up_strength"]["score"] == 30.0


class TestGaussianScore:
    def test_at_peak_returns_100(self):
        assert _gaussian_score(value=-5.5, peak=-5.5, sigma=2.5) == 100.0

    def test_far_from_peak_returns_low(self):
        assert _gaussian_score(value=20.0, peak=-5.5, sigma=2.5) < 1.0

    def test_one_sigma_returns_about_60(self):
        score = _gaussian_score(value=-3.0, peak=-5.5, sigma=2.5)
        assert 55 < score < 65


class TestConstantsExposed:
    def test_limit_up_pct_is_9_5(self):
        assert LIMIT_UP_PCT == 9.5
