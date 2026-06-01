"""compute_liquidity_risk 测试。

构造 fixture:5 只股票,amount 分别为 [100, 1000, 50000, 200000, 500000](千元),
对应横截面分位数(rank pct):0.2 / 0.4 / 0.6 / 0.8 / 1.0。

注意:amount 来自 daily_cn 表(不是 daily_basic_cn),所以 fixture 放在 ScreenerData.daily。
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from pulse_core.screener.base import PickContext, ScreenerData
from pulse_core.screener.risk_dimensions import compute_liquidity_risk


def _make_daily() -> pd.DataFrame:
    df = pd.DataFrame({
        "ts_code": ["A.SZ", "B.SZ", "C.SZ", "D.SZ", "E.SZ"],
        "amount":  [100.0, 1000.0, 50000.0, 200000.0, 500000.0],
    })
    return df.set_index("ts_code")


def _make_data(daily: pd.DataFrame) -> ScreenerData:
    empty = pd.DataFrame()
    return ScreenerData(
        daily=daily, basic=empty, moneyflow=empty,
        trend=empty, momentum=empty, volume=empty, moneyflow_ind=empty,
        history=empty, stocks=empty,
        trade_date=date(2026, 5, 21),
        universe=list(daily.index),
    )


def _make_ctx(ts_code: str, daily: pd.DataFrame, data: ScreenerData) -> PickContext:
    return PickContext(
        ts_code=ts_code,
        trade_date=data["trade_date"],
        daily=daily.loc[ts_code],
        basic=pd.Series(dtype=float),
        moneyflow=None,
        trend=pd.Series(dtype=float),
        momentum=pd.Series(dtype=float),
        volume=pd.Series(dtype=float),
        moneyflow_ind=None,
        history=pd.DataFrame(),
        data=data,
    )


class TestLiquidityRisk:
    def test_top_amount_yields_max_score(self) -> None:
        daily = _make_daily()
        data = _make_data(daily)
        result = compute_liquidity_risk(_make_ctx("E.SZ", daily, data))
        assert result["score"] == 100.0
        assert result["details"]["amount"] == 500000.0
        assert result["details"]["amount_rank_pct"] == 1.0

    def test_bottom_amount_yields_min_score(self) -> None:
        daily = _make_daily()
        data = _make_data(daily)
        result = compute_liquidity_risk(_make_ctx("A.SZ", daily, data))
        assert result["score"] == 20.0
        assert result["details"]["amount_rank_pct"] == 0.2

    def test_middle_rank(self) -> None:
        daily = _make_daily()
        data = _make_data(daily)
        result = compute_liquidity_risk(_make_ctx("C.SZ", daily, data))
        assert result["score"] == 60.0

    def test_source_format(self) -> None:
        daily = _make_daily()
        data = _make_data(daily)
        result = compute_liquidity_risk(_make_ctx("A.SZ", daily, data))
        assert result["source"] == "shared:liquidity_risk"
        assert result["weight"] == 1.0

    def test_missing_amount_raises(self) -> None:
        daily = pd.DataFrame({
            "ts_code": ["A.SZ"],
            "amount":  [float("nan")],
        }).set_index("ts_code")
        data = _make_data(daily)
        with pytest.raises(ValueError, match="amount 为空/NaN"):
            compute_liquidity_risk(_make_ctx("A.SZ", daily, data))
