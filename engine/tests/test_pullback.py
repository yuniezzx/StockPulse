import pandas as pd

from screener.pullback import PullbackScreener


def _make_today(**overrides) -> pd.Series:
    base = {
        "close_qfq": 10.5,
        "open_qfq": 10.3,
        "low_qfq": 10.1,
        "ma20": 10.2,
        "ma60": 9.5,
        "vol_ratio_5": 0.7,
    }
    base.update(overrides)
    return pd.Series(base)


class TestScore:
    def setup_method(self):
        self.s = PullbackScreener()

    def test_perfect_case_full_score(self):
        today = _make_today(
            close_qfq=10.5,
            open_qfq=10.3,
            low_qfq=10.1,
            ma20=10.2,
            vol_ratio_5=0.7,
        )
        touched_ma20 = True
        trend_gain = 0.20
        pullback_depth = 0.08
        score, reasons = self.s._score(today, touched_ma20, trend_gain, pullback_depth)
        assert score == 100
        assert {r["dim"] for r in reasons} == {
            "trigger",
            "touch",
            "volume",
            "candle",
            "trend_strength",
            "pullback_depth",
        }

    def test_trigger_always_30(self):
        today = _make_today(close_qfq=10.0, open_qfq=10.5, vol_ratio_5=2.0)
        score, reasons = self.s._score(today, False, 0.05, 0.0)
        trigger = next(r for r in reasons if r["dim"] == "trigger")
        assert trigger["score"] == 30

    def test_sum_of_reasons_equals_score(self):
        today = _make_today()
        score, reasons = self.s._score(today, True, 0.20, 0.08)
        assert sum(r["score"] for r in reasons) == score

    def test_touch_true_20(self):
        today = _make_today()
        score, reasons = self.s._score(today, True, 0.05, 0.0)
        touch = next(r for r in reasons if r["dim"] == "touch")
        assert touch["score"] == 20
        assert touch["text"] == "盘中触及 MA20"

    def test_touch_false_10(self):
        today = _make_today()
        score, reasons = self.s._score(today, False, 0.05, 0.0)
        touch = next(r for r in reasons if r["dim"] == "touch")
        assert touch["score"] == 10
        assert touch["text"] == "接近 MA20"

    def test_volume_shrink_20(self):
        today = _make_today(vol_ratio_5=0.7)
        score, reasons = self.s._score(today, True, 0.05, 0.0)
        vol = next(r for r in reasons if r["dim"] == "volume")
        assert vol["score"] == 20
        assert vol["text"] == "缩量回踩"

    def test_volume_normal_10(self):
        today = _make_today(vol_ratio_5=1.0)
        score, reasons = self.s._score(today, True, 0.05, 0.0)
        vol = next(r for r in reasons if r["dim"] == "volume")
        assert vol["score"] == 10

    def test_volume_heavy_no_score(self):
        today = _make_today(vol_ratio_5=1.5)
        score, reasons = self.s._score(today, True, 0.05, 0.0)
        assert not any(r["dim"] == "volume" for r in reasons)

    def test_candle_bullish_10(self):
        today = _make_today(close_qfq=10.5, open_qfq=10.3)
        score, reasons = self.s._score(today, True, 0.05, 0.0)
        candle = next(r for r in reasons if r["dim"] == "candle")
        assert candle["score"] == 10

    def test_candle_bearish_no_score(self):
        today = _make_today(close_qfq=10.3, open_qfq=10.5)
        score, reasons = self.s._score(today, True, 0.05, 0.0)
        assert not any(r["dim"] == "candle" for r in reasons)

    def test_trend_strong_10(self):
        today = _make_today()
        score, reasons = self.s._score(today, True, 0.20, 0.0)
        trend = next(r for r in reasons if r["dim"] == "trend_strength")
        assert trend["score"] == 10

    def test_trend_weak_no_score(self):
        today = _make_today()
        score, reasons = self.s._score(today, True, 0.10, 0.0)
        assert not any(r["dim"] == "trend_strength" for r in reasons)

    def test_pullback_depth_healthy_10(self):
        today = _make_today()
        score, reasons = self.s._score(today, True, 0.05, 0.08)
        depth = next(r for r in reasons if r["dim"] == "pullback_depth")
        assert depth["score"] == 10

    def test_pullback_depth_too_shallow_no_score(self):
        today = _make_today()
        score, reasons = self.s._score(today, True, 0.05, 0.03)
        assert not any(r["dim"] == "pullback_depth" for r in reasons)

    def test_pullback_depth_too_deep_no_score(self):
        today = _make_today()
        score, reasons = self.s._score(today, True, 0.05, 0.20)
        assert not any(r["dim"] == "pullback_depth" for r in reasons)

    def test_reasons_have_required_keys(self):
        today = _make_today()
        score, reasons = self.s._score(today, True, 0.20, 0.08)
        for r in reasons:
            assert set(r.keys()) == {"text", "score", "max", "dim"}
