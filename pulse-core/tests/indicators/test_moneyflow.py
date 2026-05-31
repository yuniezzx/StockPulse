"""moneyflow 指标单元测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pulse_core.indicators.moneyflow import compute_main_net, compute_retail_net


def _make_main_net(values: list[float] | np.ndarray, amount: float | list[float] = 10_000.0) -> pd.DataFrame:
    """辅助：生成主力净额测试数据。"""
    if isinstance(amount, list):
        amounts = amount
    else:
        amounts = [amount] * len(values)
    return pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": pd.bdate_range("2024-01-02", periods=len(values)),
            "buy_lg_amount": np.asarray(values, dtype=float) + 100.0,
            "buy_elg_amount": np.full(len(values), 50.0),
            "sell_lg_amount": np.full(len(values), 100.0),
            "sell_elg_amount": np.full(len(values), 50.0),
            "amount": amounts,
        }
    )


def _make_retail_net(values: list[float] | np.ndarray) -> pd.DataFrame:
    """辅助：生成散户净额测试数据。"""
    return pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": pd.bdate_range("2024-01-02", periods=len(values)),
            "buy_sm_amount": np.asarray(values, dtype=float) + 30.0,
            "buy_md_amount": np.full(len(values), 20.0),
            "sell_sm_amount": np.full(len(values), 30.0),
            "sell_md_amount": np.full(len(values), 20.0),
        }
    )


def test_main_net_values_ratio_and_ma5():
    result = compute_main_net(_make_main_net([100.0, 200.0, 300.0, 400.0, 500.0], 10_000.0))
    assert np.isclose(result["main_net_amount"].iloc[4], 500.0)
    assert np.isclose(result["main_net_ratio"].iloc[4], 0.05)
    assert np.isclose(result["main_net_amount_ma5"].iloc[4], 300.0)


def test_main_net_ma5_first_four_rows_null():
    result = compute_main_net(_make_main_net(np.arange(1, 6, dtype=float)))
    assert result["main_net_amount_ma5"].iloc[:4].isna().all()
    assert np.isclose(result["main_net_amount_ma5"].iloc[4], 3.0)


def test_main_net_ratio_zero_amount_null():
    result = compute_main_net(_make_main_net([100.0], 0.0))
    assert np.isclose(result["main_net_amount"].iloc[0], 100.0)
    assert pd.isna(result["main_net_ratio"].iloc[0])


def test_main_net_multi_stock_ma5_no_cross_contamination():
    dates = pd.bdate_range("2024-01-02", periods=5)
    stock_a = _make_main_net(np.arange(1, 6, dtype=float))
    stock_b = _make_main_net(np.arange(101, 106, dtype=float))
    stock_a["ts_code"] = "000001.SZ"
    stock_b["ts_code"] = "000002.SZ"
    stock_a["trade_date"] = dates
    stock_b["trade_date"] = dates
    result = compute_main_net(pd.concat([stock_a, stock_b], ignore_index=True))
    sub_a = result[result["ts_code"] == "000001.SZ"].reset_index(drop=True)
    sub_b = result[result["ts_code"] == "000002.SZ"].reset_index(drop=True)
    assert np.isclose(sub_a["main_net_amount_ma5"].iloc[4], 3.0)
    assert np.isclose(sub_b["main_net_amount_ma5"].iloc[4], 103.0)


def test_main_net_nan_propagates():
    df = _make_main_net([100.0])
    df.loc[0, "sell_elg_amount"] = np.nan
    result = compute_main_net(df)
    assert pd.isna(result["main_net_amount"].iloc[0])
    assert pd.isna(result["main_net_ratio"].iloc[0])


def test_main_net_does_not_mutate_input():
    df = _make_main_net(np.arange(1, 6, dtype=float))
    before = df.copy()
    compute_main_net(df)
    pd.testing.assert_frame_equal(df, before)


def test_main_net_negative_amount_allowed():
    result = compute_main_net(_make_main_net([-200.0], 10_000.0))
    assert np.isclose(result["main_net_amount"].iloc[0], -200.0)
    assert np.isclose(result["main_net_ratio"].iloc[0], -0.02)


def test_retail_net_values():
    result = compute_retail_net(_make_retail_net([100.0, 200.0]))
    assert np.isclose(result["retail_net_amount"].iloc[0], 100.0)
    assert np.isclose(result["retail_net_amount"].iloc[1], 200.0)


def test_retail_net_multi_stock_row_level_independent():
    dates = pd.bdate_range("2024-01-02", periods=2)
    stock_a = _make_retail_net([100.0, 200.0])
    stock_b = _make_retail_net([300.0, 400.0])
    stock_a["ts_code"] = "000001.SZ"
    stock_b["ts_code"] = "000002.SZ"
    stock_a["trade_date"] = dates
    stock_b["trade_date"] = dates
    result = compute_retail_net(pd.concat([stock_a, stock_b], ignore_index=True))
    assert result["retail_net_amount"].tolist() == [100.0, 200.0, 300.0, 400.0]


def test_retail_net_nan_propagates():
    df = _make_retail_net([100.0])
    df.loc[0, "buy_md_amount"] = np.nan
    result = compute_retail_net(df)
    assert pd.isna(result["retail_net_amount"].iloc[0])


def test_retail_net_negative_amount_allowed():
    result = compute_retail_net(_make_retail_net([-50.0]))
    assert np.isclose(result["retail_net_amount"].iloc[0], -50.0)
