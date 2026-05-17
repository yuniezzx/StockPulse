from datetime import date

from screener.base import Pick, Screener


class LimitUpScreener(Screener):
    name = "limit_up"

    async def run(self, trade_date: date) -> list[Pick]:
        # stub: 返回固定假数据
        return [
            Pick(ts_code="300750.SZ", score=95.0, signals={"stub": True}),
            Pick(ts_code="002594.SZ", score=88.0, signals={"stub": True}),
            Pick(ts_code="300059.SZ", score=80.0, signals={"stub": True}),
        ]
