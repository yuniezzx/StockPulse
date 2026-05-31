from __future__ import annotations

import pandas as pd

from tests.fixtures.synthetic import N_ROWS, TS_CODE, synthetic_adj_factor, synthetic_ohlcv


def test_synthetic_ohlcv_shape():
    df = synthetic_ohlcv()

    assert len(df) == N_ROWS
    expected_cols = {
        "ts_code",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "vol",
        "amount",
        "pre_close",
    }
    assert expected_cols.issubset(df.columns)


def test_synthetic_ohlcv_determinism():
    df1 = synthetic_ohlcv()
    df2 = synthetic_ohlcv()
    pd.testing.assert_frame_equal(df1, df2)


def test_synthetic_ohlcv_invariants():
    df = synthetic_ohlcv()

    assert (df["ts_code"] == TS_CODE).all()
    assert (df["high"] >= df["low"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["high"] >= df["open"]).all()
    assert (df["low"] <= df["close"]).all()
    assert (df["low"] <= df["open"]).all()
    assert (df["vol"] > 0).all()


def test_synthetic_adj_factor_split_pattern():
    df = synthetic_adj_factor()

    assert len(df) == N_ROWS
    assert (df["adj_factor"].iloc[:30] == 1.0).all()
    assert (df["adj_factor"].iloc[30:] == 1.5).all()


def test_synthetic_ohlcv_and_adj_dates_aligned():
    ohlcv = synthetic_ohlcv()
    adj = synthetic_adj_factor()
    pd.testing.assert_series_equal(
        ohlcv["trade_date"].reset_index(drop=True),
        adj["trade_date"].reset_index(drop=True),
    )
