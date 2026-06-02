"""Layer 1 Filter 测试:st_filter / new_stock_filter / low_liquidity_filter。"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from pulse_core.screener.contracts import ScreenerData
from pulse_core.screener.filters.universal.low_liquidity_filter import LowLiquidityFilter
from pulse_core.screener.filters.universal.new_stock_filter import NewStockFilter
from pulse_core.screener.filters.universal.st_filter import STFilter


def _make_stocks(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows).set_index("ts_code")


def _make_data(
    *,
    stocks: pd.DataFrame | None = None,
    history: pd.DataFrame | None = None,
    universe: list[str] | None = None,
    trade_date: date = date(2026, 5, 21),
) -> ScreenerData:
    empty = pd.DataFrame()
    return ScreenerData(
        daily=empty,
        basic=empty,
        moneyflow=empty,
        trend=empty, momentum=empty, volume=empty, moneyflow_ind=empty,
        history=history if history is not None else empty,
        stocks=stocks if stocks is not None else empty,
        trade_date=trade_date,
        universe=universe if universe is not None else [],
    )


class TestSTFilter:
    def test_filter_st_stocks(self) -> None:
        stocks = _make_stocks([
            {"ts_code": "000001.SZ", "name": "平安银行"},
            {"ts_code": "000002.SZ", "name": "ST 嘉陵"},
            {"ts_code": "000003.SZ", "name": "*ST 海马"},
            {"ts_code": "000004.SZ", "name": "中飞退"},
            {"ts_code": "000005.SZ", "name": "正常股"},
        ])
        data = _make_data(stocks=stocks, universe=list(stocks.index))
        result = STFilter().apply(data)
        assert result.passed == {"000001.SZ", "000005.SZ"}
        assert set(result.rejected) == {"000002.SZ", "000003.SZ", "000004.SZ"}
        assert result.rejected["000002.SZ"]["detail"]["matched_keyword"] == "ST"
        assert result.rejected["000004.SZ"]["detail"]["matched_keyword"] == "退"

    def test_missing_in_stocks_cn_rejected(self) -> None:
        stocks = _make_stocks([{"ts_code": "000001.SZ", "name": "平安银行"}])
        data = _make_data(stocks=stocks, universe=["000001.SZ", "999999.SZ"])
        result = STFilter().apply(data)
        assert result.passed == {"000001.SZ"}
        assert result.rejected["999999.SZ"]["reason"] == "missing_in_stocks_cn"


class TestNewStockFilter:
    def test_filter_new_stocks(self) -> None:
        stocks = _make_stocks([
            {"ts_code": "OLD.SZ", "list_date": pd.Timestamp("2020-01-01")},
            {"ts_code": "NEW.SZ", "list_date": pd.Timestamp("2026-04-01")},
            {"ts_code": "EDGE.SZ", "list_date": pd.Timestamp("2026-03-22")},
        ])
        data = _make_data(
            stocks=stocks,
            universe=list(stocks.index),
            trade_date=date(2026, 5, 21),
        )
        result = NewStockFilter().apply(data)
        assert "OLD.SZ" in result.passed
        assert "NEW.SZ" in result.rejected
        assert result.rejected["NEW.SZ"]["detail"]["days_since_list"] == 50
        assert "EDGE.SZ" in result.passed

    def test_missing_list_date_rejected(self) -> None:
        stocks = _make_stocks([{"ts_code": "X.SZ", "list_date": pd.NaT}])
        data = _make_data(stocks=stocks, universe=["X.SZ"])
        result = NewStockFilter().apply(data)
        assert result.rejected["X.SZ"]["reason"] == "missing_list_date"


class TestLowLiquidityFilter:
    def _make_history(self, rows: list[dict[str, object]]) -> pd.DataFrame:
        return pd.DataFrame(rows).set_index(["ts_code", "trade_date"])

    def test_filter_low_liquidity(self) -> None:
        rows = []
        for d in pd.date_range("2026-05-15", periods=5):
            rows.append({"ts_code": "GOOD.SZ", "trade_date": d, "amount": 10000.0})
            rows.append({"ts_code": "BAD.SZ", "trade_date": d, "amount": 100.0})
        history = self._make_history(rows)
        data = _make_data(history=history, universe=["GOOD.SZ", "BAD.SZ"])
        result = LowLiquidityFilter().apply(data)
        assert result.passed == {"GOOD.SZ"}
        assert "BAD.SZ" in result.rejected
        assert result.rejected["BAD.SZ"]["reason"] == "low_liquidity"
        assert result.rejected["BAD.SZ"]["detail"]["amount_5d_avg"] == 100.0

    def test_missing_history_rejected(self) -> None:
        history = self._make_history([
            {"ts_code": "A.SZ", "trade_date": pd.Timestamp("2026-05-21"), "amount": 10000.0},
        ])
        data = _make_data(history=history, universe=["A.SZ", "MISSING.SZ"])
        result = LowLiquidityFilter().apply(data)
        assert result.passed == {"A.SZ"}
        assert result.rejected["MISSING.SZ"]["reason"] == "missing_history"

    def test_history_without_amount_column_raises(self) -> None:
        history = pd.DataFrame({
            "ts_code": ["A.SZ"],
            "trade_date": [pd.Timestamp("2026-05-21")],
            "close": [10.0],
        }).set_index(["ts_code", "trade_date"])
        data = _make_data(history=history, universe=["A.SZ"])
        with pytest.raises(ValueError, match="history 缺少 amount"):
            LowLiquidityFilter().apply(data)
