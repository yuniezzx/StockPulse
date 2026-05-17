from datetime import date

from screener.base import Pick, Screener


class BreakoutScreener(Screener):
    name = "breakout"

    async def run(self, trade_date: date) -> list[Pick]:
        # stub: 返回固定假数据
        return [
            Pick(ts_code="600519.SH", score=92.5, signals={"stub": True}),
            Pick(ts_code="000001.SZ", score=85.0, signals={"stub": True}),
            Pick(ts_code="300750.SZ", score=78.3, signals={"stub": True}),
        ]
