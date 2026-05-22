"""Ingest A-share stock master data from Tushare into stocks_cn table.

默认行为：全市场一次性拉取上市股票元数据（含 BSE），全量 upsert 到 stocks_cn。
支持 CLI 参数：--dry-run（--start / --end / --stocks / --limit 对元数据全量接口无意义，会被忽略）

用法:
    # 全量同步上市股票元数据
    uv run python -m pulse_core.ingestion.stocks_cn

    # 只拉取不写库
    uv run python -m pulse_core.ingestion.stocks_cn --dry-run
"""

import asyncio
from typing import Any

import pandas as pd
from loguru import logger

from pulse_core.lib.dates import parse_date
from pulse_core.lib.db import acquire, close_pool
from pulse_core.lib.tushare_client import get_pro_client, tushare_retry

from ._cli import IngestionArgs, parse_args

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


def _clean_str(value: Any) -> str | None:
    """Normalize Tushare string fields; NaN/empty -> None."""
    if pd.isna(value) or value == "":
        return None
    return str(value).strip() or None


@tushare_retry
def _fetch_stock_basic() -> pd.DataFrame:
    """Fetch listed A-share stock basic data from Tushare."""
    pro = get_pro_client()
    return pro.stock_basic(exchange="", list_status="L", fields=_STOCK_BASIC_FIELDS)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert Tushare DataFrame to executemany rows."""
    rows: list[tuple] = []
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
                parse_date(r.list_date),
                parse_date(r.delist_date),
                _clean_str(r.is_hs),
                _clean_str(r.act_name),
                _clean_str(r.act_ent_type),
            )
        )
    return rows


async def sync_stocks_cn(args: IngestionArgs) -> int:
    """Sync listed A-share stock master data into stocks_cn."""
    logger.info(f"stocks_cn sync started (dry_run={args.dry_run})")
    df = _fetch_stock_basic()
    logger.info(f"Fetched {len(df)} listed stocks from Tushare")

    if df.empty:
        logger.warning("Tushare returned empty DataFrame; aborting")
        return 0

    if args.dry_run:
        logger.info(f"DRY-RUN: would upsert {len(df)} rows into stocks_cn")
        return len(df)

    rows = _df_to_rows(df)
    async with acquire() as conn, conn.transaction():
        await conn.executemany(_UPSERT_SQL, rows)

    logger.info(f"Upserted {len(rows)} rows into stocks_cn")
    return len(rows)


async def _main() -> None:
    args = parse_args("stocks_cn")
    if args.start:
        logger.warning("--start ignored: stocks_cn uses one-shot stock_basic metadata sync")
    if args.end:
        logger.warning("--end ignored: stocks_cn uses one-shot stock_basic metadata sync")
    if args.stocks:
        logger.warning("--stocks ignored: stocks_cn sync is full-market metadata only")
    if args.limit:
        logger.warning("--limit ignored: stocks_cn sync is not count-based")
    try:
        await sync_stocks_cn(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
