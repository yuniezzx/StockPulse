"""Ingest A-share individual stock money flow from Tushare.

Source: pro.moneyflow(trade_date='YYYYMMDD')
Unit normalization: 手 → 股 (× 100), 万元 → 元 (× 10000)
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
INSERT INTO moneyflow_cn (
    ts_code, trade_date,
    buy_sm_vol, buy_sm_amount, sell_sm_vol, sell_sm_amount,
    buy_md_vol, buy_md_amount, sell_md_vol, sell_md_amount,
    buy_lg_vol, buy_lg_amount, sell_lg_vol, sell_lg_amount,
    buy_elg_vol, buy_elg_amount, sell_elg_vol, sell_elg_amount,
    net_mf_vol, net_mf_amount
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    buy_sm_vol = EXCLUDED.buy_sm_vol,
    buy_sm_amount = EXCLUDED.buy_sm_amount,
    sell_sm_vol = EXCLUDED.sell_sm_vol,
    sell_sm_amount = EXCLUDED.sell_sm_amount,
    buy_md_vol = EXCLUDED.buy_md_vol,
    buy_md_amount = EXCLUDED.buy_md_amount,
    sell_md_vol = EXCLUDED.sell_md_vol,
    sell_md_amount = EXCLUDED.sell_md_amount,
    buy_lg_vol = EXCLUDED.buy_lg_vol,
    buy_lg_amount = EXCLUDED.buy_lg_amount,
    sell_lg_vol = EXCLUDED.sell_lg_vol,
    sell_lg_amount = EXCLUDED.sell_lg_amount,
    buy_elg_vol = EXCLUDED.buy_elg_vol,
    buy_elg_amount = EXCLUDED.buy_elg_amount,
    sell_elg_vol = EXCLUDED.sell_elg_vol,
    sell_elg_amount = EXCLUDED.sell_elg_amount,
    net_mf_vol = EXCLUDED.net_mf_vol,
    net_mf_amount = EXCLUDED.net_mf_amount
"""


@tushare_retry
def _fetch_moneyflow(trade_date: str) -> pd.DataFrame:
    pro = get_pro_client()
    return pro.moneyflow(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    rows = []
    for r in df.itertuples(index=False):
        rows.append(
            (
                r.ts_code,
                parse_date(r.trade_date),
                scale(to_float(r.buy_sm_vol), 100),
                scale(to_float(r.buy_sm_amount), 10000),
                scale(to_float(r.sell_sm_vol), 100),
                scale(to_float(r.sell_sm_amount), 10000),
                scale(to_float(r.buy_md_vol), 100),
                scale(to_float(r.buy_md_amount), 10000),
                scale(to_float(r.sell_md_vol), 100),
                scale(to_float(r.sell_md_amount), 10000),
                scale(to_float(r.buy_lg_vol), 100),
                scale(to_float(r.buy_lg_amount), 10000),
                scale(to_float(r.sell_lg_vol), 100),
                scale(to_float(r.sell_lg_amount), 10000),
                scale(to_float(r.buy_elg_vol), 100),
                scale(to_float(r.buy_elg_amount), 10000),
                scale(to_float(r.sell_elg_vol), 100),
                scale(to_float(r.sell_elg_amount), 10000),
                scale(to_float(r.net_mf_vol), 100),
                scale(to_float(r.net_mf_amount), 10000),
            )
        )
    return rows


async def sync_moneyflow_cn() -> int:
    async with acquire() as conn:
        start, end = await resolve_date_range(conn, "moneyflow_cn")
        trading_days = await fetch_trading_days(conn, start, end)
    if not trading_days:
        logger.info("No trading days in range; nothing to do")
        return 0
    logger.info(f"Found {len(trading_days)} trading days: {trading_days[0]} → {trading_days[-1]}")
    total_rows = 0
    for i, d in enumerate(trading_days, 1):
        date_str = d.strftime("%Y%m%d")
        df = _fetch_moneyflow(date_str)
        if df.empty:
            logger.warning(f"Empty moneyflow data for {d}; skipping")
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
    logger.info(f"Done, total {total_rows} rows into moneyflow_cn")
    return total_rows


async def _main() -> None:
    try:
        await sync_moneyflow_cn()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
