"""低流动性过滤。

判定规则:近 5 个交易日均成交额 < MIN_AMOUNT_5D_AVG → 剔除。
单位:千元(Tushare daily_basic.amount 原生单位)。
默认阈值 5000(= 500 万元);低于此线意味着无法承接最小持仓体量。

注意 lookback=5(需要历史窗口),Runner 必须确保 history 包含足够数据。
"""

from __future__ import annotations

from typing import cast

import pandas as pd

from pulse_core.screener.contracts import FilterResult, ScreenerData


class LowLiquidityFilter:
    name = "low_liquidity_filter"
    layer = 1
    lookback = 5
    description = "剔除近 5 日均成交额 < 500 万元的低流动性股票"
    min_amount_5d_avg: float = 5000.0

    def apply(self, data: ScreenerData) -> FilterResult:
        history = data["history"]
        universe = data["universe"]
        passed: set[str] = set()
        rejected: dict[str, dict[str, object]] = {}

        if "amount" not in history.columns:
            raise ValueError(
                "low_liquidity_filter: history 缺少 amount 列,"
                "Runner 阶段 0 应 JOIN daily_basic_cn 提供"
            )

        recent = history.groupby(level="ts_code", sort=False).tail(self.lookback)
        amount_avg = cast(pd.Series, recent.groupby(level="ts_code")["amount"].mean())

        for ts_code in universe:
            avg = amount_avg.get(ts_code)
            if avg is None or pd.isna(avg):
                rejected[ts_code] = {
                    "reason": "missing_history",
                    "detail": {},
                }
                continue
            if avg < self.min_amount_5d_avg:
                rejected[ts_code] = {
                    "reason": "low_liquidity",
                    "detail": {
                        "amount_5d_avg": round(float(avg), 2),
                        "threshold":     self.min_amount_5d_avg,
                    },
                }
            else:
                passed.add(ts_code)

        return FilterResult(name=self.name, passed=passed, rejected=rejected)
