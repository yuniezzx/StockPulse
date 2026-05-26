"""基于 close_qfq 计算趋势类指标。

所有均线使用 `rolling(window=N, min_periods=N).mean()`，因此窗口不足时严格保留为 NULL。
调用方需先完成前复权转换并提供 `close_qfq` 列。
"""

from __future__ import annotations

import pandas as pd


def compute_ma(df: pd.DataFrame) -> pd.DataFrame:
    """计算 MA5/MA10/MA20/MA60 及多头排列标记。"""
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
    result.loc[~result[["ma5", "ma10", "ma20", "ma60"]].notna().all(axis=1), "is_ma_bull_arrangement"] = pd.NA

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


