"""Ingest A-share daily adjustment factor from Tushare into adj_factor_cn table.

Source: pro.adj_factor(trade_date='YYYYMMDD')
Usage:
  后复权价 = 原始价 × adj_factor
  前复权价 = 原始价 × adj_factor / 最新 adj_factor
"""

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
    to_float,
)
from lib.db import acquire, close_pool
from lib.tushare.client import get_pro_client, tushare_retry

_UPSERT_SQL = """
INSERT INTO adj_factor_cn (
    ts_code, trade_date, adj_factor
) VALUES (
    $1, $2, $3
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    adj_factor = EXCLUDED.adj_factor
"""


@tushare_retry
def _fetch_adj_factor(trade_date: str) -> pd.DataFrame:
    pro = get_pro_client()
    return pro.adj_factor(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    rows = []
    for r in df.itertuples(index=False):
        adj = to_float(r.adj_factor)
        if adj is None:
            continue
        rows.append((r.ts_code, parse_date(r.trade_date), adj))
    return rows


async def sync_adj_factor_cn() -> int:
    async with acquire() as conn:
        start, end = await resolve_date_range(conn, "adj_factor_cn")
        trading_days = await fetch_trading_days(conn, start, end)
    if not trading_days:
        logger.info("No trading days in range; nothing to do")
        return 0
    logger.info(f"Found {len(trading_days)} trading days: {trading_days[0]} → {trading_days[-1]}")
    total_rows = 0
    for i, d in enumerate(trading_days, 1):
        date_str = d.strftime("%Y%m%d")
        df = _fetch_adj_factor(date_str)
        if df.empty:
            logger.warning(f"Empty adj_factor data for {d}; skipping")
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
    logger.info(f"Done, total {total_rows} rows into adj_factor_cn")
    return total_rows


async def _main() -> None:
    try:
        await sync_adj_factor_cn()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
