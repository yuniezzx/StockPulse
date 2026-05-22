"""Ingest A-share trading calendar from Tushare into trade_cal_cn table.

默认范围：HISTORY_START_DATE → 当年 12-31（覆盖全部历史 + 本年度）
支持 CLI 参数：--start / --end / --dry-run（--stocks / --limit 对日历无意义，会被忽略）

用法:
    # 全量（默认）
    uv run python -m pulse_core.ingestion.trade_cal_cn

    # 限定范围
    uv run python -m pulse_core.ingestion.trade_cal_cn --start 20260101 --end 20261231

    # 只拉取不写库
    uv run python -m pulse_core.ingestion.trade_cal_cn --dry-run
"""

import asyncio
from datetime import date

import pandas as pd
from loguru import logger

from pulse_core.lib.config import HISTORY_START_DATE
from pulse_core.lib.dates import parse_date
from pulse_core.lib.db import acquire, close_pool
from pulse_core.lib.tushare_client import get_pro_client, tushare_retry

from ._cli import IngestionArgs, parse_args

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


@tushare_retry
def _fetch_trade_cal(exchange: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch trade calendar from Tushare for a given exchange."""
    pro = get_pro_client()
    return pro.trade_cal(exchange=exchange, start_date=start_date, end_date=end_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert Tushare DataFrame to executemany rows."""
    rows: list[tuple] = []
    for r in df.itertuples(index=False):
        rows.append(
            (
                r.exchange,
                parse_date(r.cal_date),
                int(r.is_open),
                parse_date(r.pretrade_date),
            )
        )
    return rows


async def sync_trade_cal_cn(args: IngestionArgs) -> int:
    """Sync trade calendar for both SSE and SZSE.

    Returns total rows upserted (0 if dry-run).
    """
    start = args.start or HISTORY_START_DATE
    end = args.end or date(date.today().year, 12, 31)
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    logger.info(f"trade_cal_cn sync range: {start_str} -> {end_str} (dry_run={args.dry_run})")

    total = 0
    for exchange in _EXCHANGES:
        logger.info(f"Fetching {exchange} {start_str}-{end_str}...")
        df = _fetch_trade_cal(exchange, start_str, end_str)
        logger.info(f"Fetched {len(df)} rows for {exchange}")
        if df.empty:
            logger.warning(f"Tushare returned empty DataFrame for {exchange}; skipping")
            continue

        if args.dry_run:
            logger.info(f"DRY-RUN: would upsert {len(df)} rows for {exchange}")
            total += len(df)
            continue

        rows = _df_to_rows(df)
        async with acquire() as conn, conn.transaction():
            await conn.executemany(_UPSERT_SQL, rows)
        logger.info(f"Upserted {len(rows)} rows for {exchange}")
        total += len(rows)

    logger.info(f"Done, total {total} rows {'(dry-run)' if args.dry_run else 'into trade_cal_cn'}")
    return total


async def _main() -> None:
    args = parse_args("trade_cal_cn")
    if args.stocks:
        logger.warning("--stocks ignored: trade_cal_cn is per-exchange, not per-stock")
    if args.limit:
        logger.warning("--limit ignored: trade_cal_cn syncs by date range, not by count")
    try:
        await sync_trade_cal_cn(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
