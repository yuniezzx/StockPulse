"""Ingest A-share daily adjustment factor from Tushare into adj_factor_cn table.

默认行为：增量同步日度复权因子。
- 表为空：HISTORY_START_DATE -> today
- 表非空：MAX(trade_date) 回看 3 个交易日后 -> today

支持 CLI 参数：--start / --end / --dry-run（--stocks / --limit 对按日全市场接口无意义，会被忽略）

用法:
    # 增量同步（默认）
    uv run python -m pulse_core.ingestion.adj_factor_cn

    # 限定范围 dry-run
    uv run python -m pulse_core.ingestion.adj_factor_cn --start 20260520 --end 20260520 --dry-run
"""

import asyncio
from datetime import date

import pandas as pd
from loguru import logger

from pulse_core.lib.converters import to_float
from pulse_core.lib.dates import parse_date
from pulse_core.lib.db import acquire, close_pool
from pulse_core.lib.tushare_client import get_pro_client, tushare_retry

from ._base import PROGRESS_INTERVAL, SLEEP_BETWEEN_CALLS, fetch_trading_days, resolve_date_range
from ._cli import IngestionArgs, parse_args

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
    """Fetch full-market daily adjustment factor data for one trade date from Tushare."""
    pro = get_pro_client()
    return pro.adj_factor(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple[str, date, float]]:
    """Convert Tushare DataFrame to executemany rows."""
    rows: list[tuple[str, date, float]] = []
    for ts_code, trade_date_raw, adj_factor_raw in df[
        ["ts_code", "trade_date", "adj_factor"]
    ].itertuples(index=False, name=None):
        adj_factor = to_float(adj_factor_raw)
        if adj_factor is None:
            continue
        trade_date = parse_date(trade_date_raw)
        if trade_date is None:
            continue
        rows.append(
            (
                str(ts_code),
                trade_date,
                adj_factor,
            )
        )
    return rows


async def sync_adj_factor_cn(args: IngestionArgs) -> int:
    """Sync A-share daily adjustment factor data into adj_factor_cn."""
    async with acquire() as conn:
        start, end = await resolve_date_range(conn, "adj_factor_cn", args.start, args.end)
        trading_days = await fetch_trading_days(conn, start, end)

    logger.info(f"adj_factor_cn sync range: {start} -> {end} (dry_run={args.dry_run})")

    if not trading_days:
        logger.info("No trading days in range; nothing to do")
        return 0

    logger.info(f"Found {len(trading_days)} trading days")

    total = 0
    for i, trading_day in enumerate(trading_days, 1):
        trade_date = trading_day.strftime("%Y%m%d")
        df = _fetch_adj_factor(trade_date)

        if df.empty:
            logger.warning(f"Empty adj_factor data for {trading_day}; skipping")
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

    logger.info(f"Done, total {total} rows {'(dry-run)' if args.dry_run else 'into adj_factor_cn'}")
    return total


async def _main() -> None:
    args = parse_args("adj_factor_cn")
    if args.stocks:
        logger.warning("--stocks ignored: adj_factor_cn fetches full market per trade day")
    if args.limit:
        logger.warning("--limit ignored: adj_factor_cn syncs by trade date range, not by count")
    try:
        await sync_adj_factor_cn(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
