import pandas as pd

from screener.macd_cross import MACDCrossScreener


def _make_today(**overrides) -> pd.Series:
    base = {
        "dif": 0.15,
        "dea": 0.08,
        "hist": 0.07,
        "close_qfq": 12.34,
        "ma20": 11.50,
        "ma60": 11.20,
        "vol_ratio_5": 1.80,
    }
    base.update(overrides)
    return pd.Series(base)


class TestScore:
    def setup_method(self):
        self.s = MACDCrossScreener()

    def test_perfect_case_full_score(self):
        score, reasons = self.s._score(_make_today())
        assert score == 100
        assert len(reasons) == 5
        assert {r["dim"] for r in reasons} == {"zero_axis", "trend", "volume", "histogram"}

    def test_sum_of_reasons_equals_score(self):
        for vol_ratio in [0.5, 1.0, 1.5, 2.0]:
            today = _make_today(vol_ratio_5=vol_ratio)
            score, reasons = self.s._score(today)
            assert sum(r["score"] for r in reasons) == score, (
                f"vol_ratio={vol_ratio}: sum={sum(r['score'] for r in reasons)} != score={score}"
            )

    def test_no_zero_axis_no_score(self):
        score, reasons = self.s._score(_make_today(dif=-0.5))
        dims = {r["dim"] for r in reasons}
        assert "zero_axis" not in dims
        assert score == 60

    def test_no_volume_loses_20(self):
        score, reasons = self.s._score(_make_today(vol_ratio_5=1.0))
        dims = {r["dim"] for r in reasons}
        assert "volume" not in dims
        assert score == 80

    def test_no_trend_loses_30(self):
        score, reasons = self.s._score(_make_today(close_qfq=10.0))
        dims = {r["dim"] for r in reasons}
        assert "trend" not in dims
        assert score == 70

    def test_partial_trend_ma20_only(self):
        today = _make_today(close_qfq=11.80, ma20=11.50, ma60=12.00)
        score, reasons = self.s._score(today)
        trend_reasons = [r for r in reasons if r["dim"] == "trend"]
        assert len(trend_reasons) == 1
        assert trend_reasons[0]["text"] == "站上 MA20"

    def test_no_histogram_loses_10(self):
        score, reasons = self.s._score(_make_today(hist=-0.01))
        dims = {r["dim"] for r in reasons}
        assert "histogram" not in dims
        assert score == 90

    def test_reasons_have_required_keys(self):
        _, reasons = self.s._score(_make_today())
        for r in reasons:
            assert set(r.keys()) == {"text", "score", "max", "dim"}
            assert r["score"] == r["max"]

    def test_volume_threshold_boundary(self):
        _, reasons_below = self.s._score(_make_today(vol_ratio_5=1.49))
        _, reasons_at = self.s._score(_make_today(vol_ratio_5=1.5))
        assert "volume" not in {r["dim"] for r in reasons_below}
        assert "volume" in {r["dim"] for r in reasons_at}
