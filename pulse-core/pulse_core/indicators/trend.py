"""基于 close_qfq 计算趋势类指标。

- MA：rolling(window=N, min_periods=N).mean()，不足窗口期严格为 NULL
- EMA：ewm(span=N, adjust=False).mean()，从第一天起即有值
- MACD：基于 EMA12/EMA26 派生，需先调用 compute_ema

调用方需先完成前复权转换并提供 `close_qfq` 列。
"""

from __future__ import annotations

import pandas as pd


def compute_ma(df: pd.DataFrame) -> pd.DataFrame:
    """计算 MA5/MA10/MA20/MA60 及多头排列标记"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    for window in (5, 10, 20, 60):
        result[f"ma{window}"] = (
            result.groupby("ts_code", sort=False)["close_qfq"]
            .transform(lambda s, w=window: s.rolling(window=w, min_periods=w).mean())
        )

    bull = (
        result[["ma5", "ma10", "ma20", "ma60"]].notna().all(axis=1)
        & (result["ma5"] > result["ma10"])
        & (result["ma10"] > result["ma20"])
        & (result["ma20"] > result["ma60"])
    )
    result["is_ma_bull_arrangement"] = bull.astype("boolean")
    any_null = ~result[["ma5", "ma10", "ma20", "ma60"]].notna().all(axis=1)
    result.loc[any_null, "is_ma_bull_arrangement"] = pd.NA

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def compute_ema(df: pd.DataFrame) -> pd.DataFrame:
    """计算 EMA12/EMA26"""
    result = df.copy()

    for span in (12, 26):
        result[f"ema{span}"] = result.groupby("ts_code")["close_qfq"].transform(
            lambda s, sp=span: s.ewm(span=sp, adjust=False).mean()
        )

    return result


def compute_macd(df: pd.DataFrame) -> pd.DataFrame:
    """计算 DIF / DEA / HIST / 金叉标记"""
    result = df.copy()

    result["dif"] = result["ema12"] - result["ema26"]

    result["dea"] = result.groupby("ts_code")["dif"].transform(
        lambda s: s.ewm(span=9, adjust=False).mean()
    )

    result["hist"] = (result["dif"] - result["dea"]) * 2  # A 股惯例 ×2

    # 金叉：前一日 dif <= dea，今日 dif > dea
    prev_dif = result.groupby("ts_code")["dif"].shift(1)
    prev_dea = result.groupby("ts_code")["dea"].shift(1)
    golden = (prev_dif <= prev_dea) & (result["dif"] > result["dea"])
    any_null = result[["dif", "dea"]].isna().any(axis=1) | prev_dif.isna() | prev_dea.isna()
    result["is_macd_golden_cross"] = golden.astype("boolean")
    result.loc[any_null, "is_macd_golden_cross"] = pd.NA

    return result
