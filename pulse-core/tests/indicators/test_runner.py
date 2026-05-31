from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from pulse_core.indicators.runner import _compute_all_indicators, _df_to_rows


def _sources(n: int = 70) -> dict[str, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-02", periods=n).date
    close = np.arange(10, 10 + n, dtype=float)
    daily = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "vol": np.arange(1000, 1000 + n, dtype=float),
            "amount": np.arange(10000, 10000 + n, dtype=float),
        }
    )
    adj = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "adj_factor": 1.0,
        }
    )
    basic = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "turnover_rate": np.linspace(1.0, 2.0, n),
            "pe_ttm": np.linspace(10.0, 20.0, n),
            "pb": np.linspace(1.0, 2.0, n),
        }
    )
    mf = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "buy_sm_amount": np.full(n, 10.0),
            "sell_sm_amount": np.full(n, 4.0),
            "buy_md_amount": np.full(n, 20.0),
            "sell_md_amount": np.full(n, 5.0),
            "buy_lg_amount": np.full(n, 30.0),
            "sell_lg_amount": np.full(n, 6.0),
            "buy_elg_amount": np.full(n, 40.0),
            "sell_elg_amount": np.full(n, 7.0),
        }
    )
    limits = pd.DataFrame(
        {
            "ts_code": "000001.SZ",
            "trade_date": dates,
            "up_limit": close + 1.0,
            "down_limit": close - 1.0,
        }
    )
    limits.loc[9, "up_limit"] = daily.loc[9, "close"]
    limits.loc[10, "down_limit"] = daily.loc[10, "close"]
    return {"daily": daily, "adj": adj, "basic": basic, "mf": mf, "limits": limits}


def test_compute_all_indicators_returns_four_tables_with_columns():
    result = _compute_all_indicators(**_sources())

    assert set(result) == {
        "daily_trend_indicators_cn",
        "daily_momentum_indicators_cn",
        "daily_volume_indicators_cn",
        "daily_moneyflow_indicators_cn",
    }
    assert list(result["daily_trend_indicators_cn"].columns) == [
        "ts_code",
        "trade_date",
        "ma5",
        "ma10",
        "ma20",
        "ma60",
        "ema12",
        "ema26",
        "dif",
        "dea",
        "hist",
        "is_macd_golden_cross",
        "is_ma_bull_arrangement",
    ]
    assert list(result["daily_momentum_indicators_cn"].columns) == [
        "ts_code",
        "trade_date",
        "rsi6",
        "rsi12",
        "rsi24",
        "is_rsi_bull_arrangement",
        "atr14",
        "pct_chg_5d",
        "pct_chg_20d",
        "gap_pct",
        "body_pct",
        "is_new_high_60d",
        "is_new_low_60d",
        "is_limit_up",
        "is_limit_down",
    ]


def test_compute_trend_values_use_qfq_close():
    result = _compute_all_indicators(**_sources())["daily_trend_indicators_cn"]

    assert np.isclose(result.loc[4, "ma5"], np.arange(10, 15, dtype=float).mean())
    assert np.isclose(result.loc[59, "ma60"], np.arange(10, 70, dtype=float).mean())
    assert result.loc[59, "is_ma_bull_arrangement"] is np.True_


def test_compute_momentum_values_and_limit_flags():
    result = _compute_all_indicators(**_sources())["daily_momentum_indicators_cn"]

    assert np.isclose(result.loc[5, "pct_chg_5d"], 15 / 10 - 1)
    assert np.isclose(result.loc[1, "gap_pct"], (10.8 - 10) / 10)
    assert result.loc[9, "is_limit_up"] is np.True_
    assert result.loc[10, "is_limit_down"] is np.True_
    assert pd.isna(result.loc[0, "is_new_high_60d"])


def test_compute_volume_drops_rows_missing_all_basic_fields():
    sources = _sources()
    sources["basic"] = sources["basic"].iloc[:-1]

    result = _compute_all_indicators(**sources)["daily_volume_indicators_cn"]

    assert len(result) == 69
    assert date(2024, 4, 8) not in set(result["trade_date"])
    assert np.isclose(result.loc[result.index[4], "vol_ma5"], np.arange(1000, 1005).mean())


def test_compute_moneyflow_uses_inner_join_and_formulas():
    sources = _sources()
    sources["mf"] = sources["mf"].iloc[1:].reset_index(drop=True)

    result = _compute_all_indicators(**sources)["daily_moneyflow_indicators_cn"]

    first = result.iloc[0]
    assert len(result) == 69
    assert first["trade_date"] == date(2024, 1, 3)
    assert first["main_net_amount"] == 57.0
    assert first["retail_net_amount"] == 21.0
    assert np.isclose(first["main_net_ratio"], 57.0 / 10001.0)


def test_compute_limit_flags_missing_limits_remain_null():
    sources = _sources()
    sources["limits"] = sources["limits"].iloc[:-1]

    result = _compute_all_indicators(**sources)["daily_momentum_indicators_cn"]

    assert pd.isna(result.iloc[-1]["is_limit_up"])
    assert pd.isna(result.iloc[-1]["is_limit_down"])


def test_df_to_rows_converts_nan_to_none():
    df = pd.DataFrame({"a": [1.0, np.nan], "b": ["x", "y"]})

    assert _df_to_rows(df) == [(1.0, "x"), (None, "y")]


def test_df_to_rows_converts_pd_na_to_none():
    df = pd.DataFrame({"a": pd.Series([pd.NA], dtype="Float64")})

    assert _df_to_rows(df) == [(None,)]


def test_df_to_rows_converts_boolean_scalars():
    df = pd.DataFrame({"a": pd.Series([True, False, pd.NA], dtype="boolean")})

    assert _df_to_rows(df) == [(True,), (False,), (None,)]
    assert all(type(row[0]) is bool for row in _df_to_rows(df)[:2])


def test_warmup_rows_can_be_trimmed_after_compute():
    result = _compute_all_indicators(**_sources())
    start = date(2024, 3, 26)
    trimmed = {name: df[df["trade_date"] >= start] for name, df in result.items()}

    assert all(df["trade_date"].min() >= start for df in trimmed.values())
    assert len(trimmed["daily_trend_indicators_cn"]) == 10
    assert not pd.isna(trimmed["daily_trend_indicators_cn"].iloc[0]["ma60"])
