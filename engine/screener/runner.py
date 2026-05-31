from datetime import date

from loguru import logger

from lib.db import acquire
from screener.base import Pick, Screener
from screener.breakout import BreakoutScreener
from screener.limit_up import LimitUpScreener
from screener.macd_cross import MACDCrossScreener
from screener.moneyflow import MoneyflowScreener
from screener.pullback import PullbackScreener

SCREENERS: list[Screener] = [
    BreakoutScreener(),
    PullbackScreener(),
    MACDCrossScreener(),
    LimitUpScreener(),
    MoneyflowScreener(),
]


async def run_screener(screener: Screener, trade_date: date) -> None:
    """跑单个策略 + 写库。失败时 log，不抛出。"""
    try:
        picks = await screener.run(trade_date)
        await write_picks(trade_date, screener.name, picks)
        logger.info(f"[{screener.name}] {len(picks)} picks saved")
    except Exception as e:
        logger.error(f"Error running screener {screener.name}: {e}")


async def write_picks(trade_date: date, strategy: str, picks: list[Pick]) -> None:
    """先删后插：保证 (trade_date, strategy) 维度数据为本次最新结果，无残留。"""
    async with acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM daily_picks WHERE trade_date = $1 AND strategy = $2",
                trade_date,
                strategy,
            )
            if not picks:
                return
            await conn.executemany(
                """
                INSERT INTO daily_picks (trade_date, ts_code, strategy, score, signals)
                VALUES ($1, $2, $3, $4, $5)
                """,
                [(trade_date, p.ts_code, strategy, p.score, p.signals) for p in picks],
            )


async def run_daily(trade_date: date) -> None:
    logger.info(f"=== daily_picks run started: {trade_date} ===")
    for screener in SCREENERS:
        await run_screener(screener, trade_date)
    logger.info(f"=== daily_picks run finished: {trade_date} ===")


# CLI
if __name__ == "__main__":
    import argparse
    import asyncio

    from lib.db import close_pool

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    td = date.fromisoformat(args.date)

    async def main():
        try:
            await run_daily(td)
        finally:
            await close_pool()

    asyncio.run(main())
