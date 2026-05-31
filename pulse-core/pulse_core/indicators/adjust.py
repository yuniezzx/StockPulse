"""前复权 (qfq) 价格计算。
基于 adj_factor 把原始 OHLCV 转成前复权口径，新增 5 列 *_qfq。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def apply_qfq(
    daily_df: pd.DataFrame,
    adj_df: pd.DataFrame,
    latest_adj: dict[str, float] | None = None,
) -> pd.DataFrame:
    """计算前复权 OHLCV，新增 open_qfq/high_qfq/low_qfq/close_qfq/vol_qfq 五列。
    公式: ratio = adj_factor / latest_adj，价格 * ratio，vol / ratio。
    Args:
        daily_df: 含 ts_code/trade_date/open/high/low/close/vol。
        adj_df: 含 ts_code/trade_date/adj_factor。
        latest_adj: 可选 {ts_code: 最新 adj}。传入则用真实最新 (T10 应从 DB 查)，
            None 则 fallback 到 adj_df 内最后一行 (要求 adj_df 是全历史)。
    """
    result = daily_df.merge(adj_df, on=["ts_code", "trade_date"], how="left")
    result = result.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

    if latest_adj is not None:
        latest = result["ts_code"].map(latest_adj)
    else:
        latest = result.groupby("ts_code")["adj_factor"].transform("last")

    ratio = result["adj_factor"] / latest.replace(0, np.nan)

    result["open_qfq"] = result["open"] * ratio
    result["high_qfq"] = result["high"] * ratio
    result["low_qfq"] = result["low"] * ratio
    result["close_qfq"] = result["close"] * ratio
    result["vol_qfq"] = result["vol"] / ratio  # 量价反向

    return result.drop(columns=["adj_factor"])
