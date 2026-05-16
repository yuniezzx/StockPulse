"""Ingest A-share daily basic metrics (valuation/turnover/market cap) from Tushare.

Source: pro.daily_basic(trade_date='YYYYMMDD')
Unit normalization: 万股 → 股 (× 10000), 万元 → 元 (× 10000)
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
    scale,
    to_float,
)
from lib.db import acquire, close_pool
from lib.tushare.client import get_pro_client, tushare_retry

_UPSERT_SQL = """
INSERT INTO daily_basic_cn (
    ts_code, trade_date, close,
    turnover_rate, turnover_rate_f, volume_ratio,
    pe, pe_ttm, pb, ps, ps_ttm,
    dv_ratio, dv_ttm,
    total_share, float_share, free_share,
    total_mv, circ_mv
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
    $11, $12, $13, $14, $15, $16, $17, $18
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    close = EXCLUDED.close,
    turnover_rate = EXCLUDED.turnover_rate,
    turnover_rate_f = EXCLUDED.turnover_rate_f,
    volume_ratio = EXCLUDED.volume_ratio,
    pe = EXCLUDED.pe,
    pe_ttm = EXCLUDED.pe_ttm,
    pb = EXCLUDED.pb,
    ps = EXCLUDED.ps,
    ps_ttm = EXCLUDED.ps_ttm,
    dv_ratio = EXCLUDED.dv_ratio,
    dv_ttm = EXCLUDED.dv_ttm,
    total_share = EXCLUDED.total_share,
    float_share = EXCLUDED.float_share,
    free_share = EXCLUDED.free_share,
    total_mv = EXCLUDED.total_mv,
    circ_mv = EXCLUDED.circ_mv
"""


@tushare_retry
def _fetch_daily_basic(trade_date: str) -> pd.DataFrame:
    pro = get_pro_client()
    return pro.daily_basic(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    rows = []
    for r in df.itertuples(index=False):
        rows.append(
            (
                r.ts_code,
                parse_date(r.trade_date),
                to_float(r.close),
                to_float(r.turnover_rate),
                to_float(r.turnover_rate_f),
                to_float(r.volume_ratio),
                to_float(r.pe),
                to_float(r.pe_ttm),
                to_float(r.pb),
                to_float(r.ps),
                to_float(r.ps_ttm),
                to_float(r.dv_ratio),
                to_float(r.dv_ttm),
                scale(to_float(r.total_share), 10000),
                scale(to_float(r.float_share), 10000),
                scale(to_float(r.free_share), 10000),
                scale(to_float(r.total_mv), 10000),
                scale(to_float(r.circ_mv), 10000),
            )
        )
    return rows


async def sync_daily_basic_cn() -> int:
    async with acquire() as conn:
        start, end = await resolve_date_range(conn, "daily_basic_cn")
        trading_days = await fetch_trading_days(conn, start, end)
    if not trading_days:
        logger.info("No trading days in range; nothing to do")
        return 0
    logger.info(f"Found {len(trading_days)} trading days: {trading_days[0]} → {trading_days[-1]}")
    total_rows = 0
    for i, d in enumerate(trading_days, 1):
        date_str = d.strftime("%Y%m%d")
        df = _fetch_daily_basic(date_str)
        if df.empty:
            logger.warning(f"Empty daily_basic data for {d}; skipping")
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
    logger.info(f"Done, total {total_rows} rows into daily_basic_cn")
    return total_rows


async def _main() -> None:
    try:
        await sync_daily_basic_cn()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
