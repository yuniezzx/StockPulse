"""僵尸股过滤(Layer 2 — 赛道专属)。

判定规则:近 N 日内至少 1 次 amount > MIN_AMOUNT 才通过。
默认 lookback=10,min_amount=100_000 千元(= 1 亿元)。
长期无人交易但未退市的"僵尸股"被剔除。

依赖 ScreenerData.history(由 Runner 阶段 0 加载,JOIN daily_basic_cn 提供 amount)。
"""

from __future__ import annotations

from typing import cast

import pandas as pd

from pulse_core.screener.contracts import FilterResult, ScreenerData


class RecentActiveFilter:
    name = "recent_active_filter"
    layer = 2
    lookback = 10
    description = "剔除近 10 日内未出现单日成交额 > 1 亿的僵尸股"
    min_amount: float = 100_000.0

    def apply(self, data: ScreenerData) -> FilterResult:
        history = data["history"]
        universe = data["universe"]
        passed: set[str] = set()
        rejected: dict[str, dict[str, object]] = {}

        if "amount" not in history.columns:
            raise ValueError(
                "recent_active_filter: history 缺少 amount 列,"
                "Runner 阶段 0 应 JOIN daily_basic_cn 提供"
            )

        recent = history.groupby(level="ts_code", sort=False).tail(self.lookback)
        max_amount = cast(pd.Series, recent.groupby(level="ts_code")["amount"].max())

        for ts_code in universe:
            peak = max_amount.get(ts_code)
            if peak is None or pd.isna(peak):
                rejected[ts_code] = {"reason": "missing_history", "detail": {}}
                continue
            if peak < self.min_amount:
                rejected[ts_code] = {
                    "reason": "inactive_zombie",
                    "detail": {
                        "max_amount_recent": round(float(peak), 2),
                        "threshold":         self.min_amount,
                        "lookback":          self.lookback,
                    },
                }
            else:
                passed.add(ts_code)

        return FilterResult(name=self.name, passed=passed, rejected=rejected)
