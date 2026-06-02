from __future__ import annotations

from datetime import date

import pandas as pd

from pulse_core.screener.contracts import ScreenerData
from pulse_core.screener.filters.track.min_price_filter import MinPriceFilter
from pulse_core.screener.filters.track.recent_active_filter import RecentActiveFilter


def _data(daily: pd.DataFrame, history: pd.DataFrame, universe: list[str]) -> ScreenerData:
    empty = pd.DataFrame().set_index(pd.Index([], name="ts_code"))
    return ScreenerData(
        daily=daily,
        basic=empty,
        moneyflow=empty,
        trend=empty,
        momentum=empty,
        volume=empty,
        moneyflow_ind=empty,
        history=history,
        stocks=empty,
        trade_date=date(2026, 5, 21),
        universe=universe,
    )


class TestMinPriceFilter:
    def test_rejects_below_threshold(self):
        daily = pd.DataFrame(
            [
                {"ts_code": "A", "close": 2.5},
                {"ts_code": "B", "close": 3.0},
                {"ts_code": "C", "close": 50.0},
            ]
        ).set_index("ts_code")
        empty_hist = pd.DataFrame().set_index(
            pd.MultiIndex.from_tuples([], names=["ts_code", "trade_date"])
        )
        result = MinPriceFilter().apply(_data(daily, empty_hist, ["A", "B", "C"]))
        assert result.passed == {"B", "C"}
        assert "A" in result.rejected
        assert result.rejected["A"]["reason"] == "price_too_low"

    def test_missing_close_rejected(self):
        daily = pd.DataFrame([{"ts_code": "A", "close": float("nan")}]).set_index("ts_code")
        empty_hist = pd.DataFrame().set_index(
            pd.MultiIndex.from_tuples([], names=["ts_code", "trade_date"])
        )
        result = MinPriceFilter().apply(_data(daily, empty_hist, ["A"]))
        assert "A" in result.rejected
        assert result.rejected["A"]["reason"] == "missing_close"


class TestRecentActiveFilter:
    def _build_history(self, ts_code: str, amounts: list[float]) -> pd.DataFrame:
        rows = [
            {
                "ts_code":    ts_code,
                "trade_date": pd.Timestamp("2026-05-01") + pd.Timedelta(days=i),
                "amount":     amt,
            }
            for i, amt in enumerate(amounts)
        ]
        return pd.DataFrame(rows).set_index(["ts_code", "trade_date"])

    def test_rejects_zombie(self):
        history = self._build_history("A", [50_000.0] * 10)
        daily = pd.DataFrame([{"ts_code": "A", "close": 10.0}]).set_index("ts_code")
        result = RecentActiveFilter().apply(_data(daily, history, ["A"]))
        assert result.passed == set()
        assert result.rejected["A"]["reason"] == "inactive_zombie"

    def test_passes_active(self):
        history = self._build_history("A", [50_000.0] * 9 + [200_000.0])
        daily = pd.DataFrame([{"ts_code": "A", "close": 10.0}]).set_index("ts_code")
        result = RecentActiveFilter().apply(_data(daily, history, ["A"]))
        assert result.passed == {"A"}

    def test_missing_history_rejected(self):
        empty_hist = pd.DataFrame().set_index(
            pd.MultiIndex.from_tuples([], names=["ts_code", "trade_date"])
        )
        empty_hist["amount"] = pd.Series(dtype=float)
        daily = pd.DataFrame([{"ts_code": "A", "close": 10.0}]).set_index("ts_code")
        result = RecentActiveFilter().apply(_data(daily, empty_hist, ["A"]))
        assert "A" in result.rejected
        assert result.rejected["A"]["reason"] == "missing_history"
