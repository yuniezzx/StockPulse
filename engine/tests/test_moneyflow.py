from screener.moneyflow import MoneyflowScreener


class TestScore:
    def setup_method(self):
        self.s = MoneyflowScreener()

    def test_perfect_case_full_score(self):
        score, reasons = self.s._score(
            main_net_ratio=0.12,
            positive_days=3,
            vol_ratio=1.5,
            elg_ratio=0.8,
        )
        assert score == 100
        assert {r["dim"] for r in reasons} == {
            "trigger",
            "net_ratio",
            "continuity",
            "volume_match",
            "elg_dominant",
        }

    def test_trigger_always_30(self):
        score, reasons = self.s._score(0.03, 2, None, None)
        trigger = next(r for r in reasons if r["dim"] == "trigger")
        assert trigger["score"] == 30

    def test_sum_of_reasons_equals_score(self):
        score, reasons = self.s._score(0.12, 3, 1.5, 0.8)
        assert sum(r["score"] for r in reasons) == score

    def test_net_ratio_extreme_30(self):
        score, reasons = self.s._score(0.15, 2, None, None)
        nr = next(r for r in reasons if r["dim"] == "net_ratio")
        assert nr["score"] == 30
        assert nr["text"] == "极强净流入"

    def test_net_ratio_strong_20(self):
        score, reasons = self.s._score(0.07, 2, None, None)
        nr = next(r for r in reasons if r["dim"] == "net_ratio")
        assert nr["score"] == 20
        assert nr["text"] == "强净流入"

    def test_net_ratio_normal_10(self):
        score, reasons = self.s._score(0.04, 2, None, None)
        nr = next(r for r in reasons if r["dim"] == "net_ratio")
        assert nr["score"] == 10
        assert nr["text"] == "净流入"

    def test_continuity_three_days_20(self):
        score, reasons = self.s._score(0.04, 3, None, None)
        c = next(r for r in reasons if r["dim"] == "continuity")
        assert c["score"] == 20

    def test_continuity_two_days_10(self):
        score, reasons = self.s._score(0.04, 2, None, None)
        c = next(r for r in reasons if r["dim"] == "continuity")
        assert c["score"] == 10

    def test_volume_match_high(self):
        score, reasons = self.s._score(0.04, 2, 1.2, None)
        v = next(r for r in reasons if r["dim"] == "volume_match")
        assert v["score"] == 10

    def test_volume_match_low_no_score(self):
        score, reasons = self.s._score(0.04, 2, 0.8, None)
        assert not any(r["dim"] == "volume_match" for r in reasons)

    def test_volume_match_none_no_score(self):
        score, reasons = self.s._score(0.04, 2, None, None)
        assert not any(r["dim"] == "volume_match" for r in reasons)

    def test_elg_dominant_high(self):
        score, reasons = self.s._score(0.04, 2, None, 0.7)
        e = next(r for r in reasons if r["dim"] == "elg_dominant")
        assert e["score"] == 10

    def test_elg_dominant_low_no_score(self):
        score, reasons = self.s._score(0.04, 2, None, 0.3)
        assert not any(r["dim"] == "elg_dominant" for r in reasons)

    def test_elg_dominant_none_no_score(self):
        score, reasons = self.s._score(0.04, 2, None, None)
        assert not any(r["dim"] == "elg_dominant" for r in reasons)

    def test_reasons_have_required_keys(self):
        score, reasons = self.s._score(0.12, 3, 1.5, 0.8)
        for r in reasons:
            assert set(r.keys()) == {"text", "score", "max", "dim"}
