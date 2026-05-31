"""momentum 指标单元测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pulse_core.indicators.momentum import (
    compute_atr,
    compute_candle_shape,
    compute_limit_flags,
    compute_new_high_low,
    compute_pct_chg,
    compute_rsi,
)


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


def _make_ohlc() -> pd.DataFrame:
    """辅助：生成带 open_qfq / high_qfq / low_qfq / close_qfq 的 DataFrame。"""
    dates = pd.bdate_range("2024-01-02", periods=30)
    close = np.arange(1, 31, dtype=float)
    return pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "open_qfq": close - 0.2,
            "high_qfq": close + 0.5,
            "low_qfq": close - 0.5,
            "close_qfq": close,
        }
    )


def test_atr14_first_14_rows_null():
    result = compute_atr(_make_ohlc())
    assert result["atr14"].iloc[:14].isna().all()


def test_atr14_row14_has_value():
    result = compute_atr(_make_ohlc())
    assert not pd.isna(result["atr14"].iloc[14])
    assert result["atr14"].iloc[14] > 0


def test_atr14_constant_range_equals_range():
    dates = pd.bdate_range("2024-01-02", periods=30)
    df = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "high_qfq": 10.5,
            "low_qfq": 9.5,
            "close_qfq": 10.0,
        }
    )
    result = compute_atr(df)
    assert np.isclose(result["atr14"].iloc[20], 1.0)


def test_atr_multi_stock_no_cross_contamination():
    dates = pd.bdate_range("2024-01-02", periods=30)
    stock_a = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "high_qfq": 10.5,
            "low_qfq": 9.5,
            "close_qfq": 10.0,
        }
    )
    stock_b = pd.DataFrame(
        {
            "ts_code": "000002.SZ",
            "trade_date": dates,
            "high_qfq": 21.0,
            "low_qfq": 19.0,
            "close_qfq": 20.0,
        }
    )
    result = compute_atr(pd.concat([stock_a, stock_b], ignore_index=True))
    sub_a = result[result["ts_code"] == "000001.SZ"].reset_index(drop=True)
    sub_b = result[result["ts_code"] == "000002.SZ"].reset_index(drop=True)
    assert np.isclose(sub_a["atr14"].iloc[20], 1.0)
    assert np.isclose(sub_b["atr14"].iloc[20], 2.0)


def test_atr_does_not_mutate_input():
    df = _make_ohlc()
    before = df.copy()
    compute_atr(df)
    pd.testing.assert_frame_equal(df, before)


def test_pct_chg_5d_first_5_rows_null():
    result = compute_pct_chg(_make_close())
    assert result["pct_chg_5d"].iloc[:5].isna().all()


def test_pct_chg_20d_first_20_rows_null():
    result = compute_pct_chg(_make_close())
    assert result["pct_chg_20d"].iloc[:20].isna().all()


def test_pct_chg_5d_correct_value():
    result = compute_pct_chg(_make_close())
    assert np.isclose(result["pct_chg_5d"].iloc[5], 5.0)


def test_pct_chg_negative():
    dates = pd.bdate_range("2024-01-02", periods=30)
    df = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(30, 0, -1, dtype=float),
        }
    )
    result = compute_pct_chg(df)
    assert np.isclose(result["pct_chg_5d"].iloc[5], 25 / 30 - 1)


def test_pct_chg_multi_stock_no_cross_contamination():
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
            "close_qfq": np.arange(101, 131, dtype=float),
        }
    )
    result = compute_pct_chg(pd.concat([stock_a, stock_b], ignore_index=True))
    sub_a = result[result["ts_code"] == "000001.SZ"].reset_index(drop=True)
    sub_b = result[result["ts_code"] == "000002.SZ"].reset_index(drop=True)
    assert np.isclose(sub_a["pct_chg_5d"].iloc[5], 5.0)
    assert np.isclose(sub_b["pct_chg_5d"].iloc[5], 106 / 101 - 1)


def test_pct_chg_does_not_mutate_input():
    df = _make_close()
    before = df.copy()
    compute_pct_chg(df)
    pd.testing.assert_frame_equal(df, before)


def test_candle_shape_first_gap_pct_null():
    result = compute_candle_shape(_make_ohlc())
    assert pd.isna(result["gap_pct"].iloc[0])
    assert not pd.isna(result["body_pct"].iloc[0])


def test_candle_shape_correct_values():
    dates = pd.bdate_range("2024-01-02", periods=2)
    df = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "open_qfq": [10.0, 11.0],
            "high_qfq": [10.5, 12.0],
            "low_qfq": [9.5, 10.8],
            "close_qfq": [10.0, 12.0],
        }
    )
    result = compute_candle_shape(df)
    assert np.isclose(result["gap_pct"].iloc[1], 0.1)
    assert np.isclose(result["body_pct"].iloc[1], 1 / 11)


def test_candle_shape_multi_stock_no_cross_contamination():
    dates = pd.bdate_range("2024-01-02", periods=2)
    stock_a = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "open_qfq": [10.0, 11.0],
            "high_qfq": [10.5, 11.5],
            "low_qfq": [9.5, 10.5],
            "close_qfq": [10.0, 11.0],
        }
    )
    stock_b = pd.DataFrame(
        {
            "ts_code": "000002.SZ",
            "trade_date": dates,
            "open_qfq": [20.0, 18.0],
            "high_qfq": [21.0, 18.5],
            "low_qfq": [19.0, 17.5],
            "close_qfq": [20.0, 18.0],
        }
    )
    result = compute_candle_shape(pd.concat([stock_a, stock_b], ignore_index=True))
    sub_a = result[result["ts_code"] == "000001.SZ"].reset_index(drop=True)
    sub_b = result[result["ts_code"] == "000002.SZ"].reset_index(drop=True)
    assert np.isclose(sub_a["gap_pct"].iloc[1], 0.1)
    assert np.isclose(sub_b["gap_pct"].iloc[1], -0.1)


def test_candle_shape_body_pct_direction():
    dates = pd.bdate_range("2024-01-02", periods=2)
    df = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "open_qfq": [10.0, 10.0],
            "high_qfq": [11.0, 10.5],
            "low_qfq": [9.5, 9.0],
            "close_qfq": [11.0, 9.0],
        }
    )
    result = compute_candle_shape(df)
    assert np.isclose(result["body_pct"].iloc[0], 0.1)
    assert np.isclose(result["body_pct"].iloc[1], -0.1)


def _make_close_60(values: list[float] | np.ndarray) -> pd.DataFrame:
    """辅助：生成 60 日窗口测试数据。"""
    dates = pd.bdate_range("2024-01-02", periods=len(values))
    return pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "close_qfq": values,
        }
    )


def test_new_high_low_first_59_rows_null():
    result = compute_new_high_low(_make_close_60(np.arange(1, 61, dtype=float)))
    assert result["is_new_high_60d"].iloc[:59].isna().all()
    assert result["is_new_low_60d"].iloc[:59].isna().all()


def test_new_high_low_day_60_calculates_correctly():
    result = compute_new_high_low(_make_close_60(np.full(60, 10.0)))
    assert result["is_new_high_60d"].iloc[59] == np.bool_(True)
    assert result["is_new_low_60d"].iloc[59] == np.bool_(True)
    assert str(result["is_new_high_60d"].dtype) == "boolean"
    assert str(result["is_new_low_60d"].dtype) == "boolean"


def test_new_high_60d_triggers_on_breakout():
    values = np.concatenate([np.arange(1, 60, dtype=float), [100.0]])
    result = compute_new_high_low(_make_close_60(values))
    assert result["is_new_high_60d"].iloc[59] == np.bool_(True)
    assert result["is_new_low_60d"].iloc[59] == np.bool_(False)


def test_new_low_60d_triggers_on_breakdown():
    values = np.concatenate([np.arange(100, 41, -1, dtype=float), [1.0]])
    result = compute_new_high_low(_make_close_60(values))
    assert result["is_new_high_60d"].iloc[59] == np.bool_(False)
    assert result["is_new_low_60d"].iloc[59] == np.bool_(True)


def test_new_high_low_multi_stock_no_cross_contamination():
    dates = pd.bdate_range("2024-01-02", periods=60)
    stock_a = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(1, 61, dtype=float),
        }
    )
    stock_b = pd.DataFrame(
        {
            "ts_code": "000002.SZ",
            "trade_date": dates,
            "close_qfq": np.arange(60, 0, -1, dtype=float),
        }
    )
    result = compute_new_high_low(pd.concat([stock_a, stock_b], ignore_index=True))
    sub_a = result[result["ts_code"] == "000001.SZ"].reset_index(drop=True)
    sub_b = result[result["ts_code"] == "000002.SZ"].reset_index(drop=True)
    assert sub_a["is_new_high_60d"].iloc[59] == np.bool_(True)
    assert sub_a["is_new_low_60d"].iloc[59] == np.bool_(False)
    assert sub_b["is_new_high_60d"].iloc[59] == np.bool_(False)
    assert sub_b["is_new_low_60d"].iloc[59] == np.bool_(True)


def _make_limit_df() -> pd.DataFrame:
    """辅助：生成未复权 close 与涨跌停价测试数据。"""
    return pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": pd.bdate_range("2024-01-02", periods=1),
            "close": [11.0],
            "up_limit": [11.0],
            "down_limit": [9.0],
        }
    )


def test_limit_up_triggers_on_exact_up_limit():
    result = compute_limit_flags(_make_limit_df())
    assert result["is_limit_up"].iloc[0] == np.bool_(True)
    assert result["is_limit_down"].iloc[0] == np.bool_(False)
    assert str(result["is_limit_up"].dtype) == "boolean"
    assert str(result["is_limit_down"].dtype) == "boolean"


def test_limit_down_triggers_on_exact_down_limit():
    df = _make_limit_df()
    df["close"] = 9.0
    result = compute_limit_flags(df)
    assert result["is_limit_up"].iloc[0] == np.bool_(False)
    assert result["is_limit_down"].iloc[0] == np.bool_(True)


def test_limit_flags_normal_day_false():
    df = _make_limit_df()
    df["close"] = 10.0
    result = compute_limit_flags(df)
    assert result["is_limit_up"].iloc[0] == np.bool_(False)
    assert result["is_limit_down"].iloc[0] == np.bool_(False)


def test_limit_up_missing_up_limit_null():
    df = _make_limit_df()
    df["up_limit"] = np.nan
    result = compute_limit_flags(df)
    assert pd.isna(result["is_limit_up"].iloc[0])
    assert result["is_limit_down"].iloc[0] == np.bool_(False)


def test_limit_flags_missing_close_null():
    df = _make_limit_df()
    df["close"] = np.nan
    result = compute_limit_flags(df)
    assert pd.isna(result["is_limit_up"].iloc[0])
    assert pd.isna(result["is_limit_down"].iloc[0])
