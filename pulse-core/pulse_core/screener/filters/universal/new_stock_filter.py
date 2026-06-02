"""次新股过滤。

判定规则:上市日期距 trade_date 不足 MIN_LIST_DAYS 个自然日 → 剔除。
默认阈值 60 自然日(约 2 个月);A 股次新股一般在上市 60 日后波动性才稳定。
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from pulse_core.screener.contracts import FilterResult, ScreenerData


class NewStockFilter:
    name = "new_stock_filter"
    layer = 1
    lookback = 0
    description = "剔除上市未满 60 个自然日的次新股"
    min_list_days: int = 60

    def apply(self, data: ScreenerData) -> FilterResult:
        stocks = data["stocks"]
        universe = data["universe"]
        trade_date = data["trade_date"]
        cutoff = pd.Timestamp(trade_date) - timedelta(days=self.min_list_days)
        passed: set[str] = set()
        rejected: dict[str, dict[str, object]] = {}

        for ts_code in universe:
            if ts_code not in stocks.index:
                rejected[ts_code] = {"reason": "missing_in_stocks_cn", "detail": {}}
                continue
            list_date = stocks.loc[ts_code, "list_date"]
            if pd.isna(list_date):
                rejected[ts_code] = {"reason": "missing_list_date", "detail": {}}
                continue
            list_ts = pd.Timestamp(list_date)
            if list_ts > cutoff:
                rejected[ts_code] = {
                    "reason": "new_stock",
                    "detail": {
                        "list_date": str(list_ts.date()),
                        "days_since_list": (pd.Timestamp(trade_date) - list_ts).days,
                    },
                }
            else:
                passed.add(ts_code)

        return FilterResult(name=self.name, passed=passed, rejected=rejected)
