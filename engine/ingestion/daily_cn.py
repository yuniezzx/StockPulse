"""Ingest A-share daily OHLCV data from Tushare into daily_cn table."""

import asyncio
import time

import pandas as pd
from loguru import logger

from ingestion.base import (
    PROGRESS_INTERVAL,
    SLEEP_BETWEEN_CALLS,
    fetch_trading_days,
    parse_date,
    resolve_date_range,
    scale,
    to_float,
)
from lib.db import acquire, close_pool
from lib.tushare.client import get_pro_client, tushare_retry

_UPSERT_SQL = """
INSERT INTO daily_cn (
    ts_code, trade_date, open, high, low, close, pre_close,
    change, pct_chg, vol, amount
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    pre_close = EXCLUDED.pre_close,
    change = EXCLUDED.change,
    pct_chg = EXCLUDED.pct_chg,
    vol = EXCLUDED.vol,
    amount = EXCLUDED.amount
"""


@tushare_retry
def _fetch_daily(trade_date: str) -> pd.DataFrame:
    pro = get_pro_client()
    return pro.daily(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    rows = []
    for r in df.itertuples(index=False):
        rows.append(
            (
                r.ts_code,
                parse_date(r.trade_date),
                to_float(r.open),
                to_float(r.high),
                to_float(r.low),
                to_float(r.close),
                to_float(r.pre_close),
                to_float(r.change),
                to_float(r.pct_chg),
                scale(to_float(r.vol), 100),
                scale(to_float(r.amount), 1000),
            )
        )
    return rows


async def sync_daily_cn() -> int:
    async with acquire() as conn:
        start, end = await resolve_date_range(conn, "daily_cn")
        trading_days = await fetch_trading_days(conn, start, end)
    if not trading_days:
        logger.info("No trading days in range; nothing to do")
        return 0
    logger.info(f"Found {len(trading_days)} trading days: {trading_days[0]} → {trading_days[-1]}")
    total_rows = 0
    for i, d in enumerate(trading_days, 1):
        date_str = d.strftime("%Y%m%d")
        df = _fetch_daily(date_str)
        if df.empty:
            logger.warning(f"Empty daily data for {d}; skipping")
            time.sleep(SLEEP_BETWEEN_CALLS)
            continue
        rows = _df_to_rows(df)
        async with acquire() as conn:
            async with conn.transaction():
                await conn.executemany(_UPSERT_SQL, rows)
        total_rows += len(rows)
        if i % PROGRESS_INTERVAL == 0 or i == len(trading_days):
            logger.info(f"Progress: {i}/{len(trading_days)} ({d}) | total upserted: {total_rows}")
        time.sleep(SLEEP_BETWEEN_CALLS)
    logger.info(f"Done, total {total_rows} rows into daily_cn")
    return total_rows


async def _main() -> None:
    try:
        await sync_daily_cn()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
