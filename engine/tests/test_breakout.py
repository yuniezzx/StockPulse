import pandas as pd

from screener.breakout import BreakoutScreener


def _make_today(**overrides) -> pd.Series:
    base = {
        "close_qfq": 11.0,
        "high_qfq": 11.2,
        "low_qfq": 10.5,
        "vol_ratio_5": 1.8,
        "ma60": 9.5,
    }
    base.update(overrides)
    return pd.Series(base)


class TestScore:
    def setup_method(self):
        self.s = BreakoutScreener()

    def test_perfect_case_full_score(self):
        today = _make_today(
            close_qfq=11.0,
            high_qfq=11.1,
            low_qfq=10.5,
            vol_ratio_5=1.8,
            ma60=9.5,
        )
        prev_high = 10.6
        score, reasons = self.s._score(today, prev_high)
        assert score == 100
        assert {r["dim"] for r in reasons} == {
            "trigger",
            "volume",
            "strength",
            "trend",
            "close_position",
        }

    def test_trigger_always_30(self):
        today = _make_today(vol_ratio_5=0.5, ma60=20.0, high_qfq=11.0, low_qfq=11.0)
        prev_high = 11.0
        _, reasons = self.s._score(today, prev_high)
        trigger = [r for r in reasons if r["dim"] == "trigger"]
        assert len(trigger) == 1
        assert trigger[0]["score"] == 30

    def test_sum_of_reasons_equals_score(self):
        for vol, pct, ma60 in [
            (0.5, 0.001, 20.0),
            (1.2, 0.02, 9.0),
            (1.8, 0.05, 9.0),
            (2.0, 0.001, 20.0),
        ]:
            today = _make_today(close_qfq=11.0, vol_ratio_5=vol, ma60=ma60)
            prev_high = 11.0 / (1 + pct)
            score, reasons = self.s._score(today, prev_high)
            assert sum(r["score"] for r in reasons) == score, (
                f"vol={vol} pct={pct} ma60={ma60}: sum mismatch"
            )

    def test_volume_heavy_30(self):
        today = _make_today(vol_ratio_5=1.5)
        _, reasons = self.s._score(today, 10.5)
        volume = [r for r in reasons if r["dim"] == "volume"]
        assert len(volume) == 1
        assert volume[0]["score"] == 30

    def test_volume_moderate_15(self):
        today = _make_today(vol_ratio_5=1.0)
        _, reasons = self.s._score(today, 10.5)
        volume = [r for r in reasons if r["dim"] == "volume"]
        assert len(volume) == 1
        assert volume[0]["score"] == 15

    def test_volume_low_no_score(self):
        today = _make_today(vol_ratio_5=0.8)
        _, reasons = self.s._score(today, 10.5)
        assert "volume" not in {r["dim"] for r in reasons}

    def test_strength_strong_20(self):
        today = _make_today(close_qfq=11.0)
        prev_high = 10.0
        _, reasons = self.s._score(today, prev_high)
        strength = [r for r in reasons if r["dim"] == "strength"]
        assert len(strength) == 1
        assert strength[0]["score"] == 20
        assert strength[0]["text"] == "强力突破"

    def test_strength_effective_10(self):
        today = _make_today(close_qfq=11.0)
        prev_high = 10.85
        _, reasons = self.s._score(today, prev_high)
        strength = [r for r in reasons if r["dim"] == "strength"]
        assert len(strength) == 1
        assert strength[0]["score"] == 10
        assert strength[0]["text"] == "有效突破"

    def test_strength_weak_no_score(self):
        today = _make_today(close_qfq=11.0)
        prev_high = 10.95
        _, reasons = self.s._score(today, prev_high)
        assert "strength" not in {r["dim"] for r in reasons}

    def test_trend_above_ma60(self):
        today = _make_today(close_qfq=11.0, ma60=10.0)
        _, reasons = self.s._score(today, 10.5)
        trend = [r for r in reasons if r["dim"] == "trend"]
        assert len(trend) == 1
        assert trend[0]["score"] == 10

    def test_trend_below_ma60_no_score(self):
        today = _make_today(close_qfq=11.0, ma60=12.0)
        _, reasons = self.s._score(today, 10.5)
        assert "trend" not in {r["dim"] for r in reasons}

    def test_close_position_strong(self):
        today = _make_today(close_qfq=11.0, high_qfq=11.1, low_qfq=10.5)
        _, reasons = self.s._score(today, 10.5)
        cp = [r for r in reasons if r["dim"] == "close_position"]
        assert len(cp) == 1
        assert cp[0]["score"] == 10

    def test_close_position_weak_no_score(self):
        today = _make_today(close_qfq=10.6, high_qfq=11.1, low_qfq=10.5)
        _, reasons = self.s._score(today, 10.0)
        assert "close_position" not in {r["dim"] for r in reasons}

    def test_close_position_zero_range_skipped(self):
        today = _make_today(close_qfq=11.0, high_qfq=11.0, low_qfq=11.0)
        _, reasons = self.s._score(today, 10.5)
        assert "close_position" not in {r["dim"] for r in reasons}

    def test_reasons_have_required_keys(self):
        today = _make_today()
        _, reasons = self.s._score(today, 10.5)
        for r in reasons:
            assert set(r.keys()) == {"text", "score", "max", "dim"}
