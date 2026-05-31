"""Ingest A-share daily price limit (up/down limit) from Tushare into stk_limit_cn.

默认行为：增量同步日度涨跌停价。
- 表为空：HISTORY_START_DATE -> today
- 表非空：MAX(trade_date) 回看 3 个交易日后 -> today

支持 CLI 参数：--start / --end / --dry-run（--stocks / --limit 对按日全市场接口无意义，会被忽略）

用法:
    # 增量同步（默认）
    uv run python -m pulse_core.ingestion.stk_limit_cn

    # 限定范围 dry-run
    uv run python -m pulse_core.ingestion.stk_limit_cn --start 20260520 --end 20260520 --dry-run
"""

import asyncio

import pandas as pd
from loguru import logger

from pulse_core.lib.converters import to_float
from pulse_core.lib.dates import parse_date
from pulse_core.lib.db import acquire, close_pool
from pulse_core.lib.tushare_client import get_pro_client, tushare_retry

from ._base import PROGRESS_INTERVAL, SLEEP_BETWEEN_CALLS, fetch_trading_days, resolve_date_range
from ._cli import IngestionArgs, parse_args

_UPSERT_SQL = """
INSERT INTO stk_limit_cn (
    ts_code, trade_date, up_limit, down_limit
) VALUES (
    $1, $2, $3, $4
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    up_limit = EXCLUDED.up_limit,
    down_limit = EXCLUDED.down_limit
"""


@tushare_retry
def _fetch_stk_limit(trade_date: str) -> pd.DataFrame:
    """Fetch full-market daily price limit data for one trade date from Tushare."""
    pro = get_pro_client()
    return pro.stk_limit(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert Tushare DataFrame to executemany rows. Skip rows with NULL up/down limit."""
    rows: list[tuple] = []
    for r in df.itertuples(index=False):
        up_limit = to_float(r.up_limit)
        down_limit = to_float(r.down_limit)
        if up_limit is None or down_limit is None:
            continue
        rows.append(
            (
                r.ts_code,
                parse_date(r.trade_date),
                up_limit,
                down_limit,
            )
        )
    return rows


async def sync_stk_limit_cn(args: IngestionArgs) -> int:
    """Sync A-share daily price limit data into stk_limit_cn."""
    async with acquire() as conn:
        start, end = await resolve_date_range(conn, "stk_limit_cn", args.start, args.end)
        trading_days = await fetch_trading_days(conn, start, end)

    logger.info(f"stk_limit_cn sync range: {start} -> {end} (dry_run={args.dry_run})")

    if not trading_days:
        logger.info("No trading days in range; nothing to do")
        return 0

    logger.info(f"Found {len(trading_days)} trading days")

    total = 0
    for i, trading_day in enumerate(trading_days, 1):
        trade_date = trading_day.strftime("%Y%m%d")
        df = _fetch_stk_limit(trade_date)

        if df.empty:
            logger.warning(f"Empty stk_limit data for {trading_day}; skipping")
            await asyncio.sleep(SLEEP_BETWEEN_CALLS)
            continue

        rows = _df_to_rows(df)

        if args.dry_run:
            logger.info(f"DRY-RUN: would upsert {len(rows)} rows for {trading_day}")
            total += len(rows)
        else:
            async with acquire() as conn, conn.transaction():
                await conn.executemany(_UPSERT_SQL, rows)
            logger.info(f"Upserted {len(rows)} rows for {trading_day}")
            total += len(rows)

        if i % PROGRESS_INTERVAL == 0 or i == len(trading_days):
            logger.info(f"Progress: {i}/{len(trading_days)} ({trading_day}) | total: {total}")

        await asyncio.sleep(SLEEP_BETWEEN_CALLS)

    logger.info(f"Done, total {total} rows {'(dry-run)' if args.dry_run else 'into stk_limit_cn'}")
    return total


async def _main() -> None:
    args = parse_args("stk_limit_cn")
    if args.stocks:
        logger.warning("--stocks ignored: stk_limit_cn fetches full market per trade day")
    if args.limit:
        logger.warning("--limit ignored: stk_limit_cn syncs by trade date range, not by count")
    try:
        await sync_stk_limit_cn(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
