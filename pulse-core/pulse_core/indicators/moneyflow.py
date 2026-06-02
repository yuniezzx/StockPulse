"""基于资金流向与成交额计算资金流向派生指标。

- main_net：基于 moneyflow_cn 大单 + 特大单计算主力净流入金额、占成交额比例与 5 日均值，
  金额单位=元，比例单位=无，不足窗口期严格为 NULL
- retail_net：基于 moneyflow_cn 小单 + 中单计算散户净流入金额，金额单位=元，
  输入缺失时自然传播 NULL

调用方需提供 `ts_code` / `trade_date`，以及对应函数所需的 moneyflow_cn 金额列；
main_net 额外需要 daily_cn.amount。
"""

from __future__ import annotations

import pandas as pd


def compute_main_net(df: pd.DataFrame) -> pd.DataFrame:
    """计算主力净流入金额、占比、5 日均值"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    result["main_net_amount"] = (result["buy_lg_amount"] + result["buy_elg_amount"]) - (
        result["sell_lg_amount"] + result["sell_elg_amount"]
    )
    result["main_net_ratio"] = result["main_net_amount"] / result["amount"]
    result.loc[result["amount"] == 0, "main_net_ratio"] = pd.NA
    result["main_net_amount_ma5"] = (
        result.groupby("ts_code", sort=False)["main_net_amount"]
        .transform(lambda s: s.rolling(5, min_periods=5).mean())
    )

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def compute_retail_net(df: pd.DataFrame) -> pd.DataFrame:
    """计算散户净流入金额"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    result["retail_net_amount"] = (result["buy_sm_amount"] + result["buy_md_amount"]) - (
        result["sell_sm_amount"] + result["sell_md_amount"]
    )

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result
