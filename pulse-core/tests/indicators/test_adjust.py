"""apply_qfq 单元测试。"""

import os

import numpy as np
import pandas as pd
import pytest

from pulse_core.indicators.adjust import apply_qfq
from tests.fixtures.synthetic import synthetic_adj_factor, synthetic_ohlcv


def test_no_split_ratio_is_one():
    """无拆股 → ratio=1 → qfq 列等于原列。"""
    daily = synthetic_ohlcv()
    adj = synthetic_adj_factor()
    adj["adj_factor"] = 1.0
    result = apply_qfq(daily, adj)
    pd.testing.assert_series_equal(result["close_qfq"], result["close"], check_names=False)
    pd.testing.assert_series_equal(
        result["vol_qfq"], result["vol"].astype(float), check_names=False
    )


def test_with_split_ratio_correct():
    """fixture 拆股 1.0→1.5：前段 ratio=0.667，末段 ratio=1。"""
    result = apply_qfq(synthetic_ohlcv(), synthetic_adj_factor())
    first = result.iloc[0]
    assert np.isclose(first["close_qfq"], first["close"] * (1.0 / 1.5))
    assert np.isclose(first["vol_qfq"], first["vol"] / (1.0 / 1.5))
    last = result.iloc[-1]
    assert np.isclose(last["close_qfq"], last["close"])
    assert np.isclose(last["vol_qfq"], last["vol"])


def test_multi_stocks_independent():
    """多股各自 latest 不互相污染。"""
    daily_b = synthetic_ohlcv().assign(ts_code="000002.SZ")
    adj_b = synthetic_adj_factor().assign(ts_code="000002.SZ")
    adj_b["adj_factor"] = 2.0
    daily = pd.concat([synthetic_ohlcv(), daily_b], ignore_index=True)
    adj = pd.concat([synthetic_adj_factor(), adj_b], ignore_index=True)
    result = apply_qfq(daily, adj)
    for code in ("000001.SZ", "000002.SZ"):
        sub = result[result["ts_code"] == code]
        assert np.isclose(sub["close_qfq"].iloc[-1], sub["close"].iloc[-1])


def test_does_not_mutate_input():
    """入参不可变。"""
    daily, adj = synthetic_ohlcv(), synthetic_adj_factor()
    daily_before, adj_before = daily.copy(), adj.copy()
    apply_qfq(daily, adj)
    pd.testing.assert_frame_equal(daily, daily_before)
    pd.testing.assert_frame_equal(adj, adj_before)


def test_explicit_latest_adj_overrides():
    """显式传 latest_adj 覆盖 transform 结果。"""
    result = apply_qfq(synthetic_ohlcv(), synthetic_adj_factor(), latest_adj={"000001.SZ": 3.0})
    last = result.iloc[-1]
    assert np.isclose(last["close_qfq"], last["close"] * (1.5 / 3.0))
    assert np.isclose(last["vol_qfq"], last["vol"] / (1.5 / 3.0))


@pytest.mark.skipif(not os.getenv("TUSHARE_TOKEN"), reason="无 TUSHARE_TOKEN")
def test_qfq_parity_with_tushare():
    """与 Tushare pro_bar(adj='qfq') 对账，差异 < 0.001。"""
    import tushare as ts

    pro = ts.pro_api(os.getenv("TUSHARE_TOKEN"))
    ts_code, start, end = "000001.SZ", "20240101", "20240301"
    daily = pro.daily(ts_code=ts_code, start_date=start, end_date=end)
    adj = pro.adj_factor(ts_code=ts_code)
    qfq_ref = ts.pro_bar(ts_code=ts_code, start_date=start, end_date=end, adj="qfq")
    local = apply_qfq(daily, adj)
    merged = local.merge(
        qfq_ref[["trade_date", "close"]].rename(columns={"close": "close_ref"}),
        on="trade_date",
    )
    assert (merged["close_qfq"] - merged["close_ref"]).abs().max() < 0.001
