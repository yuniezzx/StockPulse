"""compute_liquidity_risk 测试。

构造 fixture:5 只股票,amount 分别为 [100, 1000, 50000, 200000, 500000](千元),
对应横截面分位数(rank pct):0.2 / 0.4 / 0.6 / 0.8 / 1.0。
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from pulse_core.screener.base import PickContext, ScreenerData
from pulse_core.screener.risk_dimensions import compute_liquidity_risk


def _make_basic() -> pd.DataFrame:
    df = pd.DataFrame({
        "ts_code": ["A.SZ", "B.SZ", "C.SZ", "D.SZ", "E.SZ"],
        "amount":  [100.0, 1000.0, 50000.0, 200000.0, 500000.0],
    })
    return df.set_index("ts_code")


def _make_data(basic: pd.DataFrame) -> ScreenerData:
    empty = pd.DataFrame()
    return ScreenerData(
        daily=empty, basic=basic, moneyflow=empty,
        trend=empty, momentum=empty, volume=empty, moneyflow_ind=empty,
        history=empty, stocks=empty,
        trade_date=date(2026, 5, 21),
        universe=list(basic.index),
    )


def _make_ctx(ts_code: str, basic: pd.DataFrame, data: ScreenerData) -> PickContext:
    return PickContext(
        ts_code=ts_code,
        trade_date=data["trade_date"],
        daily=pd.Series(dtype=float),
        basic=basic.loc[ts_code],
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
        basic = _make_basic()
        data = _make_data(basic)
        result = compute_liquidity_risk(_make_ctx("E.SZ", basic, data))
        assert result["score"] == 100.0
        assert result["details"]["amount"] == 500000.0
        assert result["details"]["amount_rank_pct"] == 1.0

    def test_bottom_amount_yields_min_score(self) -> None:
        basic = _make_basic()
        data = _make_data(basic)
        result = compute_liquidity_risk(_make_ctx("A.SZ", basic, data))
        assert result["score"] == 20.0
        assert result["details"]["amount_rank_pct"] == 0.2

    def test_middle_rank(self) -> None:
        basic = _make_basic()
        data = _make_data(basic)
        result = compute_liquidity_risk(_make_ctx("C.SZ", basic, data))
        assert result["score"] == 60.0

    def test_source_format(self) -> None:
        basic = _make_basic()
        data = _make_data(basic)
        result = compute_liquidity_risk(_make_ctx("A.SZ", basic, data))
        assert result["source"] == "shared:liquidity_risk"
        assert result["weight"] == 1.0

    def test_missing_amount_raises(self) -> None:
        basic = pd.DataFrame({
            "ts_code": ["A.SZ"],
            "amount":  [float("nan")],
        }).set_index("ts_code")
        data = _make_data(basic)
        with pytest.raises(ValueError, match="amount 为空/NaN"):
            compute_liquidity_risk(_make_ctx("A.SZ", basic, data))
