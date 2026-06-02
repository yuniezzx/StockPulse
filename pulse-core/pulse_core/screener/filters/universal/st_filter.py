"""ST / *ST / 退市股票过滤。

判定规则:stocks_cn.name 含 "ST" / "*ST" / "退" / "PT" 关键字 → 剔除。
"""

from __future__ import annotations

from pulse_core.screener.contracts import FilterResult, ScreenerData

_REJECT_KEYWORDS: tuple[str, ...] = ("ST", "退", "PT")


class STFilter:
    name = "st_filter"
    layer = 1
    lookback = 0
    description = "剔除 ST / *ST / 退市 / PT 股票"

    def apply(self, data: ScreenerData) -> FilterResult:
        stocks = data["stocks"]
        universe = data["universe"]
        passed: set[str] = set()
        rejected: dict[str, dict[str, object]] = {}

        for ts_code in universe:
            if ts_code not in stocks.index:
                rejected[ts_code] = {
                    "reason": "missing_in_stocks_cn",
                    "detail": {},
                }
                continue
            stock_name = str(stocks.loc[ts_code, "name"])
            hit = next((kw for kw in _REJECT_KEYWORDS if kw in stock_name), None)
            if hit is not None:
                rejected[ts_code] = {
                    "reason": "st_or_delisted",
                    "detail": {"name": stock_name, "matched_keyword": hit},
                }
            else:
                passed.add(ts_code)

        return FilterResult(name=self.name, passed=passed, rejected=rejected)
