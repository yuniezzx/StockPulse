"""超低价股过滤(Layer 2 — 赛道专属)。

判定规则:当日 close < MIN_CLOSE 元 → 剔除。
默认 3.0 元;超低价股流动性差、退市风险高,scalp 赛道不参与。
"""

from __future__ import annotations

import math

from pulse_core.screener.contracts import FilterResult, ScreenerData


class MinPriceFilter:
    name = "min_price_filter"
    layer = 2
    lookback = 0
    description = "剔除当日收盘价 < 3 元的超低价股"
    min_close: float = 3.0

    def apply(self, data: ScreenerData) -> FilterResult:
        daily = data["daily"]
        universe = data["universe"]
        passed: set[str] = set()
        rejected: dict[str, dict[str, object]] = {}

        for ts_code in universe:
            if ts_code not in daily.index:
                rejected[ts_code] = {"reason": "missing_in_daily", "detail": {}}
                continue
            close = daily.loc[ts_code, "close"]
            if close is None or (isinstance(close, float) and math.isnan(close)):
                rejected[ts_code] = {"reason": "missing_close", "detail": {}}
                continue
            if close < self.min_close:
                rejected[ts_code] = {
                    "reason": "price_too_low",
                    "detail": {"close": float(close), "threshold": self.min_close},
                }
            else:
                passed.add(ts_code)

        return FilterResult(name=self.name, passed=passed, rejected=rejected)
