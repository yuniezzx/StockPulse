from datetime import date

from screener.base import Pick, Screener


class MACDCrossScreener(Screener):
    name = "macd_cross"

    async def run(self, trade_date: date) -> list[Pick]:
        # stub: 返回固定假数据
        return [
            Pick(ts_code="600036.SH", score=90.0, signals={"stub": True}),
            Pick(ts_code="000001.SZ", score=83.0, signals={"stub": True}),
            Pick(ts_code="002594.SZ", score=76.0, signals={"stub": True}),
        ]
