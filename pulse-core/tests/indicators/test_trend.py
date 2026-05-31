"""trend 指标单元测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pulse_core.indicators.adjust import apply_qfq
from pulse_core.indicators.trend import compute_ma
from tests.fixtures.synthetic import synthetic_adj_factor, synthetic_ohlcv


def _make_qfq() -> pd.DataFrame:
    """辅助：生成带 close_qfq 的 DataFrame。"""
    daily = synthetic_ohlcv()
    adj = synthetic_adj_factor()
    return apply_qfq(daily, adj)


def test_ma5_first_4_rows_null():
    result = compute_ma(_make_qfq())
    assert result["ma5"].iloc[:4].isna().all()


def test_ma5_row5_correct():
    result = compute_ma(_make_qfq())
    expected = result["close_qfq"].iloc[:5].mean()
    assert np.isclose(result["ma5"].iloc[4], expected)


def test_ma60_all_null_when_less_than_60_rows():
    df = _make_qfq().iloc[:59].reset_index(drop=True)
    result = compute_ma(df)
    assert result["ma60"].isna().all()


def test_bull_arrangement_null_when_ma_null():
    result = compute_ma(_make_qfq())
    assert result["is_ma_bull_arrangement"].iloc[:59].isna().all()


def test_bull_arrangement_true_when_ascending():
    dates = pd.bdate_range("2024-01-02", periods=70)
    df = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(1, 71, dtype=float),
        }
    )
    result = compute_ma(df)
    assert result["is_ma_bull_arrangement"].iloc[59:].all()


def test_multi_stock_no_cross_contamination():
    dates = pd.bdate_range("2024-01-02", periods=70)
    stock_a = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(1, 71, dtype=float),
        }
    )
    stock_b = pd.DataFrame(
        {
            "ts_code": "000002.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(101, 171, dtype=float),
        }
    )
    result = compute_ma(pd.concat([stock_a, stock_b], ignore_index=True))
    for code, base in (("000001.SZ", 1.0), ("000002.SZ", 101.0)):
        sub = result[result["ts_code"] == code].reset_index(drop=True)
        assert np.isclose(sub["ma5"].iloc[4], np.arange(base, base + 5).mean())
        assert sub["is_ma_bull_arrangement"].iloc[59:].all()


def test_does_not_mutate_input():
    df = _make_qfq()
    before = df.copy()
    compute_ma(df)
    pd.testing.assert_frame_equal(df, before)
