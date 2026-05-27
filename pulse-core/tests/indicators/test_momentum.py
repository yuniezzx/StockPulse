"""momentum 指标单元测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pulse_core.indicators.momentum import compute_rsi


def _make_close() -> pd.DataFrame:
    """辅助：生成带 close_qfq 的 DataFrame。"""
    dates = pd.bdate_range("2024-01-02", periods=30)
    return pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(1, 31, dtype=float),
        }
    )


def test_rsi6_first_5_rows_null():
    result = compute_rsi(_make_close())
    assert result["rsi6"].iloc[:6].isna().all()


def test_rsi24_warmup_null():
    result = compute_rsi(_make_close())
    assert result["rsi24"].iloc[:24].isna().all()


def test_rsi_monotonic_up_equals_100():
    result = compute_rsi(_make_close())
    for col, start in (("rsi6", 6), ("rsi12", 12), ("rsi24", 24)):
        assert np.isclose(result[col].iloc[start:], 100.0).all()


def test_rsi_monotonic_down_equals_0():
    dates = pd.bdate_range("2024-01-02", periods=30)
    df = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(30, 0, -1, dtype=float),
        }
    )
    result = compute_rsi(df)
    for col, start in (("rsi6", 6), ("rsi12", 12), ("rsi24", 24)):
        assert np.isclose(result[col].iloc[start:], 0.0).all()


def test_rsi_bull_arrangement_null_during_warmup():
    result = compute_rsi(_make_close())
    assert result["is_rsi_bull_arrangement"].iloc[:24].isna().all()


def test_rsi_bull_arrangement_dtype():
    result = compute_rsi(_make_close())
    assert str(result["is_rsi_bull_arrangement"].dtype) == "boolean"


def test_multi_stock_no_cross_contamination():
    dates = pd.bdate_range("2024-01-02", periods=30)
    stock_a = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(1, 31, dtype=float),
        }
    )
    stock_b = pd.DataFrame(
        {
            "ts_code": "000002.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(30, 0, -1, dtype=float),
        }
    )
    result = compute_rsi(pd.concat([stock_a, stock_b], ignore_index=True))
    for code, value in (("000001.SZ", 100.0), ("000002.SZ", 0.0)):
        sub = result[result["ts_code"] == code].reset_index(drop=True)
        assert np.isclose(sub["rsi6"].iloc[6:], value).all()
        assert np.isclose(sub["rsi12"].iloc[12:], value).all()
        assert np.isclose(sub["rsi24"].iloc[24:], value).all()


def test_does_not_mutate_input():
    df = _make_close()
    before = df.copy()
    compute_rsi(df)
    pd.testing.assert_frame_equal(df, before)
