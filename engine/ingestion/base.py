"""Shared helpers, constants, and SQL for daily-cadence Tushare ingestion."""

from datetime import date, datetime
from typing import Any

import pandas as pd
from loguru import logger

from lib.config import HISTORY_START_DATE

SLEEP_BETWEEN_CALLS = 0.5
PROGRESS_INTERVAL = 50
LOOKBACK_TRADING_DAYS = 3

TRADING_DAYS_SQL = """
SELECT cal_date FROM trade_cal_cn
WHERE exchange = 'SSE'
    AND is_open = 1
    AND cal_date BETWEEN $1 AND $2
ORDER BY cal_date
"""

LOOKBACK_START_SQL = """
SELECT cal_date FROM trade_cal_cn
WHERE exchange = 'SSE'
  AND is_open = 1
  AND cal_date <= $1
ORDER BY cal_date DESC
OFFSET $2 LIMIT 1
"""


def parse_date(s: Any) -> date | None:
    if pd.isna(s) or not s:
        return None
    try:
        return datetime.strptime(str(s), "%Y%m%d").date()
    except (ValueError, TypeError):
        return None


def to_float(v: Any) -> float | None:
    if pd.isna(v):
        return None
    return float(v)


def scale(v: float | None, factor: float) -> float | None:
    return v * factor if v is not None else None


async def resolve_date_range(conn, table_name: str) -> tuple[date, date]:
    last = await conn.fetchval(f"SELECT MAX(trade_date) FROM {table_name}")
    if last is None:
        start = HISTORY_START_DATE
        logger.info(f"Empty {table_name} table; full sync from {start}")
    else:
        start = await conn.fetchval(LOOKBACK_START_SQL, last, LOOKBACK_TRADING_DAYS - 1)
        start = start or last
        logger.info(
            f"Incremental sync from {start} "
            f"(last={last}, lookback={LOOKBACK_TRADING_DAYS} trading days)"
        )
    return start, date.today()


async def fetch_trading_days(conn, start: date, end: date) -> list[date]:
    rows = await conn.fetch(TRADING_DAYS_SQL, start, end)
    return [r["cal_date"] for r in rows]
