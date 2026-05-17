from datetime import date

from screener.base import Pick, Screener


class PullbackScreener(Screener):
    name = "pullback"

    async def run(self, trade_date: date) -> list[Pick]:
        # stub: 返回固定假数据
        return [
            Pick(ts_code="600519.SH", score=88.0, signals={"stub": True}),
            Pick(ts_code="300750.SZ", score=82.0, signals={"stub": True}),
            Pick(ts_code="601318.SH", score=75.0, signals={"stub": True}),
        ]
