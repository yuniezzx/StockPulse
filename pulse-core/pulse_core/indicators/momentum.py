"""基于 qfq 价格计算动量类指标。

- RSI：基于 Wilder 平滑，周期沿用同花顺/东方财富 A 股惯例（6/12/24），不足窗口期严格为 NULL
- ATR：True Range 的 Wilder 平滑（基于 qfq high/low/close），周期 14
- pct_chg：基于 close_qfq 的 5 日 / 20 日累计涨跌幅，单位为小数

调用方需先完成前复权转换并提供 `close_qfq` / `high_qfq` / `low_qfq` 列。
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
