import pandas as pd

from screener.limit_up import LimitUpScreener


def _make_history(today_close, today_up_limit, **kwargs):
    """生成一个 11 行的历史 df（今日 + 前 10 日），用于喂给 _score。

    kwargs 可覆盖：
      - prev_close_list: list of 前 10 日 close
      - prev_up_limit_list: list of 前 10 日 up_limit
      - today_vol: 今日 vol
      - prev_vol_list: list of 前 10 日 vol
    """
    prev_close = kwargs.get("prev_close_list", [10.0] * 10)
    prev_up_limit = kwargs.get("prev_up_limit_list", [11.0] * 10)
    today_vol = kwargs.get("today_vol", 1000.0)
    prev_vol = kwargs.get("prev_vol_list", [800.0] * 10)

    rows = [{"close": today_close, "up_limit": today_up_limit, "vol": today_vol}]
    for c, ul, v in zip(prev_close, prev_up_limit, prev_vol, strict=True):
        rows.append({"close": c, "up_limit": ul, "vol": v})
    return pd.DataFrame(rows)


class TestScore:
    def setup_method(self):
        self.s = LimitUpScreener()

    def test_perfect_case_full_score(self):
        df = _make_history(
            today_close=10.0,
            today_up_limit=10.0,
            prev_close_list=[15.0] + [14.0] * 9,
            prev_up_limit_list=[16.0] * 10,
            today_vol=1600.0,
            prev_vol_list=[800.0] * 10,
        )
        score, reasons = self.s._score(df)
        assert score == 100
        assert {r["dim"] for r in reasons} == {"trigger", "position", "volume", "price"}

    def test_trigger_always_40(self):
        df = _make_history(today_close=100.0, today_up_limit=100.0)
        _, reasons = self.s._score(df)
        trigger = [r for r in reasons if r["dim"] == "trigger"]
        assert len(trigger) == 1
        assert trigger[0]["score"] == 40

    def test_sum_of_reasons_equals_score(self):
        for close, vol in [(10.0, 800.0), (10.0, 1600.0), (50.0, 1600.0), (50.0, 3500.0)]:
            df = _make_history(
                today_close=close,
                today_up_limit=close,
                prev_close_list=[close * 1.5] * 10,
                prev_up_limit_list=[close * 1.6] * 10,
                today_vol=vol,
                prev_vol_list=[800.0] * 10,
            )
            score, reasons = self.s._score(df)
            assert sum(r["score"] for r in reasons) == score, (
                f"close={close} vol={vol}: sum mismatch"
            )

    def test_position_low_30(self):
        df = _make_history(
            today_close=7.0,
            today_up_limit=7.0,
            prev_close_list=[15.0] + [14.0] * 9,
            prev_up_limit_list=[16.0] * 10,
        )
        _, reasons = self.s._score(df)
        position = [r for r in reasons if r["dim"] == "position"]
        assert len(position) == 1
        assert position[0]["score"] == 30
        assert position[0]["text"] == "低位首板"

    def test_position_mid_15(self):
        df = _make_history(
            today_close=12.0,
            today_up_limit=12.0,
            prev_close_list=[15.0] + [14.0] * 9,
            prev_up_limit_list=[16.0] * 10,
        )
        _, reasons = self.s._score(df)
        position = [r for r in reasons if r["dim"] == "position"]
        assert len(position) == 1
        assert position[0]["score"] == 15
        assert position[0]["text"] == "中位首板"

    def test_position_high_no_score(self):
        df = _make_history(
            today_close=14.0,
            today_up_limit=14.0,
            prev_close_list=[15.0] + [14.0] * 9,
            prev_up_limit_list=[16.0] * 10,
        )
        _, reasons = self.s._score(df)
        assert "position" not in {r["dim"] for r in reasons}

    def test_volume_moderate_20(self):
        df = _make_history(
            today_close=10.0,
            today_up_limit=10.0,
            today_vol=1600.0,
            prev_vol_list=[800.0] * 10,
        )
        _, reasons = self.s._score(df)
        volume = [r for r in reasons if r["dim"] == "volume"]
        assert len(volume) == 1
        assert volume[0]["score"] == 20

    def test_volume_huge_10(self):
        df = _make_history(
            today_close=10.0,
            today_up_limit=10.0,
            today_vol=4000.0,
            prev_vol_list=[800.0] * 10,
        )
        _, reasons = self.s._score(df)
        volume = [r for r in reasons if r["dim"] == "volume"]
        assert len(volume) == 1
        assert volume[0]["score"] == 10
        assert volume[0]["text"] == "巨量涨停"

    def test_volume_low_no_score(self):
        df = _make_history(
            today_close=10.0,
            today_up_limit=10.0,
            today_vol=500.0,
            prev_vol_list=[800.0] * 10,
        )
        _, reasons = self.s._score(df)
        assert "volume" not in {r["dim"] for r in reasons}

    def test_price_low_10(self):
        df = _make_history(today_close=10.0, today_up_limit=10.0)
        _, reasons = self.s._score(df)
        price = [r for r in reasons if r["dim"] == "price"]
        assert len(price) == 1
        assert price[0]["score"] == 10

    def test_price_high_no_score(self):
        df = _make_history(today_close=50.0, today_up_limit=50.0)
        _, reasons = self.s._score(df)
        assert "price" not in {r["dim"] for r in reasons}

    def test_reasons_have_required_keys(self):
        df = _make_history(
            today_close=10.0,
            today_up_limit=10.0,
            prev_close_list=[15.0] + [14.0] * 9,
            prev_up_limit_list=[16.0] * 10,
            today_vol=1600.0,
        )
        _, reasons = self.s._score(df)
        for r in reasons:
            assert set(r.keys()) == {"text", "score", "max", "dim"}
