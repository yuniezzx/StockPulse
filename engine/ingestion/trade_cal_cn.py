"""Ingest A-share trading calendar from Tushare into trade_cal_cn table."""

import asyncio
from datetime import date, datetime
from typing import Any

import pandas as pd
from loguru import logger

from lib.config import HISTORY_START_DATE
from lib.db import acquire, close_pool
from lib.tushare.client import get_pro_client, tushare_retry

_EXCHANGES = ("SSE", "SZSE")

_UPSERT_SQL = """
INSERT INTO trade_cal_cn (
    exchange, cal_date, is_open, pretrade_date
) VALUES (
    $1, $2, $3, $4
) ON CONFLICT (exchange, cal_date) DO UPDATE SET
    is_open = EXCLUDED.is_open,
    pretrade_date = EXCLUDED.pretrade_date
"""


def _parse_date(s: Any) -> date | None:
    """Convert Tushare 'YYYYMMDD' string to date; handle NaN/empty."""
    if pd.isna(s) or not s:
        return None
    try:
        return datetime.strptime(str(s), "%Y%m%d").date()
    except (ValueError, TypeError):
        return None


@tushare_retry
def _fetch_trade_cal(exchange: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch trade calendar from Tushare for a given exchange."""
    pro = get_pro_client()
    return pro.trade_cal(exchange=exchange, start_date=start_date, end_date=end_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert DataFrame to a list of tuples ready for executemany."""
    rows = []
    for r in df.itertuples(index=False):
        rows.append(
            (
                r.exchange,
                _parse_date(r.cal_date),
                int(r.is_open),
                _parse_date(r.pretrade_date),
            )
        )
    return rows


async def sync_trade_cal_cn() -> int:
    today = date.today()
    start_str = HISTORY_START_DATE.strftime("%Y%m%d")
    end_str = today.replace(month=12, day=31).strftime("%Y%m%d")
    total = 0
    for exchange in _EXCHANGES:
        logger.info(f"Fetching trade_cal {exchange} {start_str}-{end_str}...")
        df = _fetch_trade_cal(exchange, start_str, end_str)
        logger.info(f"Fetched {len(df)} rows for {exchange}")
        if df.empty:
            logger.warning(f"Tushare returned empty DataFrame for {exchange}; skipping")
            continue
        rows = _df_to_rows(df)
        async with acquire() as conn:
            async with conn.transaction():
                await conn.executemany(_UPSERT_SQL, rows)
        logger.info(f"Upserted {len(rows)} rows for {exchange}")
        total += len(rows)
    logger.info(f"Done, total {total} rows into trade_cal_cn")
    return total


async def _main() -> None:
    try:
        await sync_trade_cal_cn()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
