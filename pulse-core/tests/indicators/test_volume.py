"""volume 指标单元测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pulse_core.indicators.volume import (
    compute_pe_pb_quantile,
    compute_turnover_ratio,
    compute_vol_ma,
)


def _make_vol(values: list[float] | np.ndarray) -> pd.DataFrame:
    """辅助：生成成交量测试数据。"""
    return pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": pd.bdate_range("2024-01-02", periods=len(values)),
            "vol": values,
        }
    )


def _make_turnover(values: list[float] | np.ndarray) -> pd.DataFrame:
    """辅助：生成换手率测试数据。"""
    return pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": pd.bdate_range("2024-01-02", periods=len(values)),
            "turnover_rate": values,
        }
    )


def _make_pe_pb(pe_values: list[float] | np.ndarray, pb_values: list[float] | np.ndarray) -> pd.DataFrame:
    """辅助：生成估值分位测试数据。"""
    return pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": pd.bdate_range("2024-01-02", periods=len(pe_values)),
            "pe_ttm": pe_values,
            "pb": pb_values,
        }
    )


def test_vol_ma_warmup_and_values():
    result = compute_vol_ma(_make_vol(np.arange(1, 11, dtype=float)))
    assert result["vol_ma5"].iloc[:4].isna().all()
    assert result["vol_ma10"].iloc[:9].isna().all()
    assert np.isclose(result["vol_ma5"].iloc[4], 3.0)
    assert np.isclose(result["vol_ma10"].iloc[9], 5.5)


def test_vol_ratio_5_correct_value():
    result = compute_vol_ma(_make_vol(np.arange(1, 6, dtype=float)))
    assert np.isclose(result["vol_ratio_5"].iloc[4], 5 / 3)


def test_vol_ratio_5_zero_denominator_null():
    result = compute_vol_ma(_make_vol(np.zeros(5, dtype=float)))
    assert np.isclose(result["vol_ma5"].iloc[4], 0.0)
    assert pd.isna(result["vol_ratio_5"].iloc[4])


def test_vol_ma_multi_stock_no_cross_contamination():
    dates = pd.bdate_range("2024-01-02", periods=5)
    stock_a = pd.DataFrame({"ts_code": "000001.SZ", "trade_date": dates, "vol": np.arange(1, 6, dtype=float)})
    stock_b = pd.DataFrame({"ts_code": "000002.SZ", "trade_date": dates, "vol": np.arange(101, 106, dtype=float)})
    result = compute_vol_ma(pd.concat([stock_a, stock_b], ignore_index=True))
    sub_a = result[result["ts_code"] == "000001.SZ"].reset_index(drop=True)
    sub_b = result[result["ts_code"] == "000002.SZ"].reset_index(drop=True)
    assert np.isclose(sub_a["vol_ma5"].iloc[4], 3.0)
    assert np.isclose(sub_b["vol_ma5"].iloc[4], 103.0)


def test_vol_ma_does_not_mutate_input():
    df = _make_vol(np.arange(1, 11, dtype=float))
    before = df.copy()
    compute_vol_ma(df)
    pd.testing.assert_frame_equal(df, before)


def test_turnover_rate_ma5_warmup_and_value():
    result = compute_turnover_ratio(_make_turnover(np.arange(1, 6, dtype=float)))
    assert result["turnover_rate_ma5"].iloc[:4].isna().all()
    assert np.isclose(result["turnover_rate_ma5"].iloc[4], 3.0)


def test_turnover_rate_ratio_5_correct_value():
    result = compute_turnover_ratio(_make_turnover(np.arange(1, 6, dtype=float)))
    assert np.isclose(result["turnover_rate_ratio_5"].iloc[4], 5 / 3)


def test_turnover_rate_ratio_5_zero_denominator_null():
    result = compute_turnover_ratio(_make_turnover(np.zeros(5, dtype=float)))
    assert np.isclose(result["turnover_rate_ma5"].iloc[4], 0.0)
    assert pd.isna(result["turnover_rate_ratio_5"].iloc[4])


def test_turnover_rate_nan_propagates():
    values = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0])
    result = compute_turnover_ratio(_make_turnover(values))
    assert result["turnover_rate_ma5"].isna().all()
    assert result["turnover_rate_ratio_5"].isna().all()


def test_turnover_rate_multi_stock_no_cross_contamination():
    dates = pd.bdate_range("2024-01-02", periods=5)
    stock_a = pd.DataFrame({"ts_code": "000001.SZ", "trade_date": dates, "turnover_rate": np.arange(1, 6, dtype=float)})
    stock_b = pd.DataFrame({"ts_code": "000002.SZ", "trade_date": dates, "turnover_rate": np.arange(11, 16, dtype=float)})
    result = compute_turnover_ratio(pd.concat([stock_a, stock_b], ignore_index=True))
    sub_a = result[result["ts_code"] == "000001.SZ"].reset_index(drop=True)
    sub_b = result[result["ts_code"] == "000002.SZ"].reset_index(drop=True)
    assert np.isclose(sub_a["turnover_rate_ma5"].iloc[4], 3.0)
    assert np.isclose(sub_b["turnover_rate_ma5"].iloc[4], 13.0)


def test_pe_pb_quantile_monotonic_last_equals_one():
    result = compute_pe_pb_quantile(_make_pe_pb(np.arange(1, 61, dtype=float), np.arange(101, 161, dtype=float)))
    assert np.isclose(result["pe_ttm_pct_60"].iloc[59], 1.0)
    assert np.isclose(result["pb_pct_60"].iloc[59], 1.0)


def test_pe_pb_quantile_first_59_rows_null():
    result = compute_pe_pb_quantile(_make_pe_pb(np.arange(1, 61, dtype=float), np.arange(1, 61, dtype=float)))
    assert result["pe_ttm_pct_60"].iloc[:59].isna().all()
    assert result["pb_pct_60"].iloc[:59].isna().all()


def test_pe_pb_quantile_window_nan_returns_null():
    pe = np.arange(1, 61, dtype=float)
    pb = np.arange(1, 61, dtype=float)
    pe[10] = np.nan
    pb[20] = np.nan
    result = compute_pe_pb_quantile(_make_pe_pb(pe, pb))
    assert pd.isna(result["pe_ttm_pct_60"].iloc[59])
    assert pd.isna(result["pb_pct_60"].iloc[59])


def test_pe_pb_quantile_multi_stock_no_cross_contamination():
    dates = pd.bdate_range("2024-01-02", periods=60)
    stock_a = pd.DataFrame(
        {"ts_code": "000001.SZ", "trade_date": dates, "pe_ttm": np.arange(1, 61, dtype=float), "pb": np.arange(1, 61, dtype=float)}
    )
    stock_b = pd.DataFrame(
        {"ts_code": "000002.SZ", "trade_date": dates, "pe_ttm": np.arange(60, 0, -1, dtype=float), "pb": np.arange(60, 0, -1, dtype=float)}
    )
    result = compute_pe_pb_quantile(pd.concat([stock_a, stock_b], ignore_index=True))
    sub_a = result[result["ts_code"] == "000001.SZ"].reset_index(drop=True)
    sub_b = result[result["ts_code"] == "000002.SZ"].reset_index(drop=True)
    assert np.isclose(sub_a["pe_ttm_pct_60"].iloc[59], 1.0)
    assert np.isclose(sub_b["pe_ttm_pct_60"].iloc[59], 0.0)
    assert np.isclose(sub_a["pb_pct_60"].iloc[59], 1.0)
    assert np.isclose(sub_b["pb_pct_60"].iloc[59], 0.0)


def test_pe_pb_quantile_negative_values_rank_normally():
    pe = np.concatenate([np.arange(-30, 29, dtype=float), [-0.5]])
    pb = np.concatenate([np.arange(-30, 29, dtype=float), [0.5]])
    result = compute_pe_pb_quantile(_make_pe_pb(pe, pb))
    assert np.isclose(result["pe_ttm_pct_60"].iloc[59], 30 / 59)
    assert np.isclose(result["pb_pct_60"].iloc[59], 31 / 59)


def test_pe_pb_quantile_does_not_mutate_input():
    df = _make_pe_pb(np.arange(1, 61, dtype=float), np.arange(1, 61, dtype=float))
    before = df.copy()
    compute_pe_pb_quantile(df)
    pd.testing.assert_frame_equal(df, before)
