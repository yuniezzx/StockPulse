"""基于成交量、换手率与估值计算量价估值类指标。

- vol_ma：基于 daily_cn.vol 的 5 日 / 10 日移动平均，单位=股，
  成交量无复权语义，不足窗口期严格为 NULL
- vol_ratio：基于 daily_cn.vol / vol_ma5，单位=无，
  vol_ma5 为 0 或窗口不足时为 NULL
- turnover_rate_ma：基于 daily_basic_cn.turnover_rate 的 5 日移动平均，
  单位=%（3.5 表示 3.5%），不足窗口期严格为 NULL
- turnover_rate_ratio：基于 turnover_rate / turnover_rate_ma5，
  单位=无，分母为 0 或窗口不足时为 NULL
- pe_pb_quantile：基于 daily_basic_cn.pe_ttm / pb 的 60 日滚动分位，
  单位=小数 [0,1]，窗口内有效样本不足 60 时严格为 NULL

调用方需提供 `ts_code` / `trade_date`，
以及对应函数所需的 `vol`、`turnover_rate`、`pe_ttm`、`pb` 列。
"""

from __future__ import annotations

import pandas as pd


def compute_vol_ma(df: pd.DataFrame) -> pd.DataFrame:
    """计算成交量 MA5/MA10 与 5 日量比"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    for window in (5, 10):
        result[f"vol_ma{window}"] = result.groupby("ts_code", sort=False)["vol"].transform(
            lambda s, w=window: s.rolling(w, min_periods=w).mean()
        )

    result["vol_ratio_5"] = result["vol"] / result["vol_ma5"]
    result.loc[result["vol_ma5"] == 0, "vol_ratio_5"] = pd.NA

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def compute_turnover_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """计算换手率 5 日均值与放大倍数"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    result["turnover_rate_ma5"] = result.groupby("ts_code", sort=False)["turnover_rate"].transform(
        lambda s: s.rolling(5, min_periods=5).mean()
    )
    result["turnover_rate_ratio_5"] = result["turnover_rate"] / result["turnover_rate_ma5"]
    result.loc[result["turnover_rate_ma5"] == 0, "turnover_rate_ratio_5"] = pd.NA

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def compute_pe_pb_quantile(df: pd.DataFrame) -> pd.DataFrame:
    """计算 PE_TTM/PB 60 日滚动分位"""
    result = df.copy()
    result["_row_order"] = range(len(result))
    result = result.sort_values(["ts_code", "trade_date", "_row_order"]).reset_index(drop=True)

    result["pe_ttm_pct_60"] = (
        result.groupby("ts_code", sort=False)["pe_ttm"].transform(_rolling_pct_60)
    )
    result["pb_pct_60"] = (
        result.groupby("ts_code", sort=False)["pb"].transform(_rolling_pct_60)
    )

    result = result.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
    return result


def _rolling_pct_60(s: pd.Series) -> pd.Series:
    return s.rolling(60, min_periods=60).apply(
        lambda x: (x.rank(method="average").iloc[-1] - 1) / 59
    )
