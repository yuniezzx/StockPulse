"""基于 qfq 价格计算动量类指标。

- RSI：基于 Wilder 平滑，周期沿用同花顺/东方财富 A 股惯例（6/12/24），不足窗口期严格为 NULL
- ATR：True Range 的 Wilder 平滑（基于 qfq high/low/close），周期 14
- pct_chg：基于 close_qfq 的 5 日 / 20 日累计涨跌幅，单位为小数
- candle_shape：基于 qfq open/close 的跳空幅度与实体幅度，单位为小数
- new_high_low：基于 close_qfq 的 60 日新高 / 新低布尔标记
- limit_flags：基于未复权 close 与 stk_limit_cn 精确涨跌停价的涨停 / 跌停标记

调用方需先完成前复权转换并提供 `open_qfq` / `close_qfq` / `high_qfq` / `low_qfq` 列。
涨跌停标记例外：必须使用未复权 `close` / `up_limit` / `down_limit` 列。
"""

from __future__ import annotations

import pandas as pd


def compute_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """计算 RSI6/RSI12/RSI24 及多头排列标记"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    for window in (6, 12, 24):
        result[f"rsi{window}"] = (
            result.groupby("ts_code", sort=False)["close_qfq"]
            .transform(lambda s, w=window: _rsi(s, w))
        )

    bull = (
        result[["rsi6", "rsi12", "rsi24"]].notna().all(axis=1)
        & (result["rsi6"] > result["rsi12"])
        & (result["rsi12"] > result["rsi24"])
    )
    result["is_rsi_bull_arrangement"] = bull.astype("boolean")
    result.loc[~result[["rsi6", "rsi12", "rsi24"]].notna().all(axis=1), "is_rsi_bull_arrangement"] = pd.NA

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def _rsi(s, window):
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    return 100 * avg_gain / (avg_gain + avg_loss)


def compute_atr(df: pd.DataFrame) -> pd.DataFrame:
    """计算 ATR14"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    prev_close = result.groupby("ts_code", sort=False)["close_qfq"].shift(1)
    tr1 = result["high_qfq"] - result["low_qfq"]
    tr2 = (result["high_qfq"] - prev_close).abs()
    tr3 = (result["low_qfq"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    tr.loc[prev_close.isna()] = pd.NA

    result["atr14"] = tr.groupby(result["ts_code"], sort=False).transform(
        lambda s: s.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    )

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def compute_pct_chg(df: pd.DataFrame) -> pd.DataFrame:
    """计算 5 日 / 20 日累计涨跌幅"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    for window in (5, 20):
        prev = result.groupby("ts_code", sort=False)["close_qfq"].shift(window)
        result[f"pct_chg_{window}d"] = result["close_qfq"] / prev - 1

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def compute_candle_shape(df: pd.DataFrame) -> pd.DataFrame:
    """计算跳空幅度与 K 线实体幅度"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    prev_close = result.groupby("ts_code", sort=False)["close_qfq"].shift(1)
    result["gap_pct"] = (result["open_qfq"] - prev_close) / prev_close
    result["body_pct"] = (result["close_qfq"] - result["open_qfq"]) / result["open_qfq"]

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def compute_new_high_low(df: pd.DataFrame) -> pd.DataFrame:
    """计算 60 日新高 / 新低标记"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    rolling_max = result.groupby("ts_code", sort=False)["close_qfq"].transform(
        lambda s: s.rolling(60, min_periods=60).max()
    )
    rolling_min = result.groupby("ts_code", sort=False)["close_qfq"].transform(
        lambda s: s.rolling(60, min_periods=60).min()
    )

    result["is_new_high_60d"] = (result["close_qfq"] >= rolling_max).astype("boolean")
    result.loc[rolling_max.isna(), "is_new_high_60d"] = pd.NA
    result["is_new_low_60d"] = (result["close_qfq"] <= rolling_min).astype("boolean")
    result.loc[rolling_min.isna(), "is_new_low_60d"] = pd.NA

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def compute_limit_flags(df: pd.DataFrame) -> pd.DataFrame:
    """计算涨停 / 跌停标记

    df 须含未复权列：close / up_limit / down_limit
    """
    result = df.copy()

    is_up = (result["close"] == result["up_limit"]).astype("boolean")
    missing_up = result["close"].isna() | result["up_limit"].isna()
    is_up.loc[missing_up] = pd.NA
    result["is_limit_up"] = is_up

    is_down = (result["close"] == result["down_limit"]).astype("boolean")
    missing_down = result["close"].isna() | result["down_limit"].isna()
    is_down.loc[missing_down] = pd.NA
    result["is_limit_down"] = is_down

    return result
