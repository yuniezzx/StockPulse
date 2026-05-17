from datetime import date

from screener.base import Pick, Screener


class MoneyflowScreener(Screener):
    name = "moneyflow"

    async def run(self, trade_date: date) -> list[Pick]:
        # stub: 返回固定假数据
        return [
            Pick(ts_code="600519.SH", score=91.0, signals={"stub": True}),
            Pick(ts_code="600036.SH", score=86.0, signals={"stub": True}),
            Pick(ts_code="300750.SZ", score=79.0, signals={"stub": True}),
        ]
