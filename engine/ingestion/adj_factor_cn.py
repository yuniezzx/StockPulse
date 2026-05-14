"""Ingest A-share daily adjustment factor from Tushare into adj_factor_cn table.

Source: pro.adj_factor(trade_date='YYYYMMDD')
Fields: ts_code, trade_date, adj_factor

Usage:
  后复权价 = 原始价 × adj_factor
  前复权价 = 原始价 × adj_factor / 最新 adj_factor
"""

import asyncio
import time
from datetime import date, datetime
from typing import Any

import pandas as pd
from loguru import logger

from lib.config import HISTORY_START_DATE
from lib.db import acquire, close_pool
from lib.tushare.client import get_pro_client, tushare_retry

_SLEEP_BETWEEN_CALLS = 0.5
_PROGRESS_INTERVAL = 50
_LOOKBACK_TRADING_DAYS = 3

_UPSERT_SQL = """
INSERT INTO adj_factor_cn (
    ts_code, trade_date, adj_factor
) VALUES (
    $1, $2, $3
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    adj_factor = EXCLUDED.adj_factor
"""

_TRADING_DAYS_SQL = """
SELECT cal_date FROM trade_cal_cn
WHERE exchange = 'SSE'
    AND is_open = 1
    AND cal_date BETWEEN $1 AND $2
ORDER BY cal_date
"""

_LOOKBACK_START_SQL = """
SELECT cal_date FROM trade_cal_cn
WHERE exchange = 'SSE'
  AND is_open = 1
  AND cal_date <= $1
ORDER BY cal_date DESC
OFFSET $2 LIMIT 1
"""


def _parse_date(s: Any) -> date | None:
    """Convert Tushare 'YYYYMMDD' string to date; handle NaN/empty."""
    if pd.isna(s) or not s:
        return None
    try:
        return datetime.strptime(str(s), "%Y%m%d").date()
    except (ValueError, TypeError):
        return None


def _to_float(v: Any) -> float | None:
    """Convert numpy/pandas numeric to Python float; NaN → None."""
    if pd.isna(v):
        return None
    return float(v)


@tushare_retry
def _fetch_adj_factor(trade_date: str) -> pd.DataFrame:
    """Fetch adjustment factor for all stocks on a given trade_date."""
    pro = get_pro_client()
    return pro.adj_factor(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert DataFrame to tuples. adj_factor is unitless, no conversion."""
    rows = []
    for r in df.itertuples(index=False):
        adj = _to_float(r.adj_factor)
        if adj is None:
            continue
        rows.append(
            (
                r.ts_code,
                _parse_date(r.trade_date),
                adj,
            )
        )
    return rows


async def _resolve_date_range(conn) -> tuple[date, date]:
    """Determine [start, end] window based on existing data."""
    last = await conn.fetchval("SELECT MAX(trade_date) FROM adj_factor_cn")
    if last is None:
        start = HISTORY_START_DATE
        logger.info(f"Empty adj_factor_cn table; full sync from {start}")
    else:
        start = await conn.fetchval(_LOOKBACK_START_SQL, last, _LOOKBACK_TRADING_DAYS - 1)
        start = start or last
        logger.info(
            f"Incremental sync from {start} "
            f"(last={last}, lookback={_LOOKBACK_TRADING_DAYS} trading days)"
        )

    return start, date.today()


async def _fetch_trading_days(conn, start: date, end: date) -> list[date]:
    """Query trade_cal_cn for trading days in [start, end]."""
    rows = await conn.fetch(_TRADING_DAYS_SQL, start, end)
    return [r["cal_date"] for r in rows]


async def sync_adj_factor_cn() -> int:
    async with acquire() as conn:
        start, end = await _resolve_date_range(conn)
        trading_days = await _fetch_trading_days(conn, start, end)
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
            time.sleep(_SLEEP_BETWEEN_CALLS)
            continue
        rows = _df_to_rows(df)
        async with acquire() as conn:
            async with conn.transaction():
                await conn.executemany(_UPSERT_SQL, rows)
        total_rows += len(rows)
        if i % _PROGRESS_INTERVAL == 0 or i == len(trading_days):
            logger.info(
                f"Progress: {i}/{len(trading_days)} ({d}) | total upserted: {total_rows}"
            )
        time.sleep(_SLEEP_BETWEEN_CALLS)
    logger.info(f"Done, total {total_rows} rows into adj_factor_cn")
    return total_rows


async def _main() -> None:
    try:
        await sync_adj_factor_cn()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
