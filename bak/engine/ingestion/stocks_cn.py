"""Ingest A-share stock master data from Tushare into stocks_cn table."""

import asyncio
from datetime import date, datetime
from typing import Any

import pandas as pd
from loguru import logger

from lib.db import acquire, close_pool
from lib.tushare.client import get_pro_client, tushare_retry

# stock_basic 接口的所有字段，与 stocks_cn 表对齐
_STOCK_BASIC_FIELDS = (
    "ts_code,symbol,name,fullname,enname,cnspell,"
    "area,industry,market,exchange,curr_type,"
    "list_status,list_date,delist_date,is_hs,"
    "act_name,act_ent_type"
)

_UPSERT_SQL = """
INSERT INTO stocks_cn (
    ts_code, symbol, name, fullname, enname, cnspell,
    area, industry, market, exchange, curr_type,
    list_status, list_date, delist_date, is_hs,
    act_name, act_ent_type
) VALUES (
    $1, $2, $3, $4, $5, $6,
    $7, $8, $9, $10, $11,
    $12, $13, $14, $15,
    $16, $17
) ON CONFLICT (ts_code) DO UPDATE SET
    symbol = EXCLUDED.symbol,
    name = EXCLUDED.name,
    fullname = EXCLUDED.fullname,
    enname = EXCLUDED.enname,
    cnspell = EXCLUDED.cnspell,
    area = EXCLUDED.area,
    industry = EXCLUDED.industry,
    market = EXCLUDED.market,
    exchange = EXCLUDED.exchange,
    curr_type = EXCLUDED.curr_type,
    list_status = EXCLUDED.list_status,
    list_date = EXCLUDED.list_date,
    delist_date = EXCLUDED.delist_date,
    is_hs = EXCLUDED.is_hs,
    act_name = EXCLUDED.act_name,
    act_ent_type = EXCLUDED.act_ent_type,
    updated_at = NOW()
"""


def _parse_date(s: Any) -> date | None:
    """Convert Tushare 'YYYYMMDD' string to date; handle NaN/empty."""
    if pd.isna(s) or not s:
        return None
    try:
        return datetime.strptime(str(s), "%Y%m%d").date()
    except (ValueError, TypeError):
        return None


def _clean_str(s: Any) -> str | None:
    """Normalize Tushare string fields; NaN/empty → None."""
    if pd.isna(s) or s == "":
        return None
    return str(s).strip() or None


@tushare_retry
def _fetch_stock_basic() -> pd.DataFrame:
    """Fetch stock basic data from Tushare."""
    pro = get_pro_client()
    return pro.stock_basic(exchange="", list_status="L", fields=_STOCK_BASIC_FIELDS)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert DataFrame to a list of tuples ready for executemany."""
    rows = []
    for r in df.itertuples(index=False):
        rows.append(
            (
                _clean_str(r.ts_code),
                _clean_str(r.symbol),
                _clean_str(r.name),
                _clean_str(r.fullname),
                _clean_str(r.enname),
                _clean_str(r.cnspell),
                _clean_str(r.area),
                _clean_str(r.industry),
                _clean_str(r.market),
                _clean_str(r.exchange),
                _clean_str(r.curr_type),
                _clean_str(r.list_status),
                _parse_date(r.list_date),
                _parse_date(r.delist_date),
                _clean_str(r.is_hs),
                _clean_str(r.act_name),
                _clean_str(r.act_ent_type),
            )
        )
    return rows


async def sync_stocks_cn() -> int:
    logger.info("Fetching stock_basic from Tushare...")
    df = _fetch_stock_basic()
    logger.info(f"Fetched {len(df)} stocks")

    if df.empty:
        logger.warning("Tushare returned empty DataFrame; aborting")
        return 0

    rows = _df_to_rows(df)

    async with acquire() as conn:
        async with conn.transaction():
            await conn.executemany(_UPSERT_SQL, rows)

    logger.info(f"Upserted {len(rows)} rows into stocks_cn")
    return len(rows)


async def _main() -> None:
    try:
        await sync_stocks_cn()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
