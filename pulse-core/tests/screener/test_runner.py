from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from pulse_core.screener.base import PickContext, Scorecard, ScreenerData
from pulse_core.screener.runner import (
    RunResult,
    TrackResult,
    _build_context,
    _run_layer1,
    _run_layer2,
    _run_strategies,
)


def _make_screener_data(trade_date: date = date(2026, 5, 21)) -> ScreenerData:
    """构造一个最小可用的 ScreenerData(3 只股票:正常 / ST / 次新)。"""
    universe = ["000001.SZ", "000002.SZ", "000003.SZ"]

    stocks = pd.DataFrame(
        [
            {
                "ts_code":     "000001.SZ",
                "name":        "平安银行",
                "list_date":   pd.Timestamp("2010-01-01"),
                "delist_date": None,
                "industry":    "银行",
            },
            {
                "ts_code":     "000002.SZ",
                "name":        "ST 万科",
                "list_date":   pd.Timestamp("2010-01-01"),
                "delist_date": None,
                "industry":    "地产",
            },
            {
                "ts_code":     "000003.SZ",
                "name":        "新次新股",
                "list_date":   pd.Timestamp("2026-04-01"),
                "delist_date": None,
                "industry":    "科技",
            },
        ]
    ).set_index("ts_code")

    daily = pd.DataFrame(
        [
            {
                "ts_code": ts,
                "open":  10.0, "high": 11.0, "low": 9.5, "close": 10.5,
                "vol":   1e6,  "pct_chg": 1.0,
            }
            for ts in universe
        ]
    ).set_index("ts_code")

    basic = pd.DataFrame(
        [
            {"ts_code": ts, "amount": 1_000_000.0, "turnover_rate": 2.0}
            for ts in universe
        ]
    ).set_index("ts_code")

    history_rows = []
    for ts in universe:
        for i in range(10):
            history_rows.append({
                "ts_code":    ts,
                "trade_date": pd.Timestamp(trade_date) - pd.Timedelta(days=10 - i),
                "open":  10.0, "high": 11.0, "low": 9.5, "close": 10.5, "vol": 1e6, "pct_chg": 1.0,
                "amount": 1_000_000.0, "turnover_rate": 2.0,
            })
    history = pd.DataFrame(history_rows).set_index(["ts_code", "trade_date"])

    empty = pd.DataFrame().set_index(pd.Index([], name="ts_code"))

    return ScreenerData(
        daily=daily,
        basic=basic,
        moneyflow=empty,
        trend=empty,
        momentum=empty,
        volume=empty,
        moneyflow_ind=empty,
        history=history,
        stocks=stocks,
        trade_date=trade_date,
        universe=universe,
    )


class TestRunLayer1:
    def test_filters_st_and_new_stock(self):
        data = _make_screener_data()
        passed = _run_layer1(data)
        assert "000001.SZ" in passed
        assert "000002.SZ" not in passed
        assert "000003.SZ" not in passed


class TestRunLayer2:
    def test_empty_filter_list_returns_all(self):
        data = _make_screener_data()
        layer1 = {"000001.SZ"}
        result = _run_layer2([], data, layer1)
        assert result == layer1

    def test_unknown_filter_raises_key_error(self):
        data = _make_screener_data()
        with pytest.raises(KeyError, match="未注册"):
            _run_layer2(["nonexistent_filter"], data, {"000001.SZ"})


class TestRunStrategies:
    def test_empty_strategies_returns_no_picks(self):
        data = _make_screener_data()
        picks = _run_strategies([], data, {"000001.SZ"})
        assert picks == []

    def test_empty_candidates_returns_no_picks(self):
        data = _make_screener_data()
        picks = _run_strategies(["any_strategy"], data, set())
        assert picks == []


class TestBuildContext:
    def test_assembles_picked_slices(self):
        data = _make_screener_data()
        ctx = _build_context("000001.SZ", data)
        assert isinstance(ctx, PickContext)
        assert ctx.ts_code == "000001.SZ"
        assert ctx.daily["close"] == 10.5
        assert ctx.basic["amount"] == 1_000_000.0


class TestRunResult:
    def test_status_all_success(self):
        result = RunResult(trade_date=date(2026, 5, 21), track_results=[
            TrackResult(track="scalp", status="success", inserted=10),
        ])
        assert result.status == "success"

    def test_status_mixed_is_partial(self):
        result = RunResult(trade_date=date(2026, 5, 21), track_results=[
            TrackResult(track="scalp", status="success", inserted=10),
            TrackResult(track="swing", status="failed", error="boom"),
        ])
        assert result.status == "partial"

    def test_status_all_failed(self):
        result = RunResult(trade_date=date(2026, 5, 21), track_results=[
            TrackResult(track="scalp", status="failed", error="x"),
            TrackResult(track="swing", status="failed", error="y"),
        ])
        assert result.status == "failed"

    def test_status_no_tracks_is_failed(self):
        result = RunResult(trade_date=date(2026, 5, 21))
        assert result.status == "failed"

    def test_to_details_serializes_track_results(self):
        result = RunResult(trade_date=date(2026, 5, 21), track_results=[
            TrackResult(track="scalp", status="success", inserted=10),
        ])
        details = result.to_details()
        assert details["trade_date"] == "2026-05-21"
        assert details["tracks"][0]["track"] == "scalp"
        assert details["tracks"][0]["inserted"] == 10


class TestRunTrackErrorIsolation:
    """单赛道失败不影响其他赛道(§7.3 partial 语义)。"""

    @pytest.mark.asyncio
    async def test_track_with_unknown_filter_returns_failed_status(self, tmp_path):
        from pulse_core.screener.runner import _run_track

        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(
            "track: bad\ntop_n: 5\nfilters:\n  - nonexistent_filter\nstrategies: []\n",
            encoding="utf-8",
        )

        data = _make_screener_data()
        with patch("pulse_core.screener.runner.write_track_picks") as mock_write:
            result = await _run_track(
                conn=None,  # type: ignore[arg-type]
                track_file=bad_yaml,
                data=data,
                layer1_passed={"000001.SZ"},
            )
        assert result.status == "failed"
        assert "未注册" in (result.error or "")
        mock_write.assert_not_called()


class TestPickRowSorting:
    """Top_n 截断按 final_score 降序。"""

    def test_sort_picks_by_final_score(self):
        from pulse_core.screener.db_writer import PickRow

        sc_high = Scorecard.build(
            reward={"r": {"score": 90.0, "weight": 1.0}},
            risk={"k": {"score": 80.0, "weight": 1.0, "source": "shared:liquidity_risk"}},
        )
        sc_low = Scorecard.build(
            reward={"r": {"score": 50.0, "weight": 1.0}},
            risk={"k": {"score": 50.0, "weight": 1.0, "source": "shared:liquidity_risk"}},
        )
        picks = [
            PickRow(ts_code="L", strategy="x", scorecard=sc_low),
            PickRow(ts_code="H", strategy="x", scorecard=sc_high),
        ]
        sorted_picks = sorted(picks, key=lambda p: p.scorecard.axis_scores["final"], reverse=True)
        assert sorted_picks[0].ts_code == "H"
