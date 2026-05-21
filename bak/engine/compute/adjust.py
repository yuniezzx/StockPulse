"""
为什么要复权？
    当股票分红、送股、配股时，股价会突然下降（除权除息），但这不是市场真实交易导致的下跌。为了让股价走势连续、便于技术分析，需要做复权处理。

前复权的计算逻辑
    用今天的价格（已除权除息）作为基准，往回推算出除权前的历史价格应该同步降低多少。
    结果：历史价格变小，但K线形态（涨跌幅度、技术指标）保持连续。
"""

import pandas as pd


def to_qfq(df: pd.DataFrame) -> pd.DataFrame:
    """前复权：以 df 最后一行的 adj_factor 为基准，加 *_qfq 列。"""
    if "adj_factor" not in df.columns:
        raise ValueError("df must have 'adj_factor' column")

    latest_af = df["adj_factor"].iloc[-1]
    out = df.copy()
    for col in ["open", "high", "low", "close"]:
        out[f"{col}_qfq"] = out[col] * out["adj_factor"] / latest_af
    return out
