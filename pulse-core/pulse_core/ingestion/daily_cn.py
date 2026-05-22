"""Ingest A-share daily OHLCV data from Tushare into daily_cn table.

默认行为：增量同步日线行情。
- 表为空：HISTORY_START_DATE -> today
- 表非空：MAX(trade_date) + 1 -> today

支持 CLI 参数：--start / --end / --dry-run（--stocks / --limit 对按日全市场接口无意义，会被忽略）

用法:
    # 增量同步（默认）
    uv run python -m pulse_core.ingestion.daily_cn

    # 限定范围 dry-run
    uv run python -m pulse_core.ingestion.daily_cn --start 20260518 --end 20260522 --dry-run
"""

import asyncio
from datetime import date, timedelta

import pandas as pd
from loguru import logger

from pulse_core.lib.config import HISTORY_START_DATE
from pulse_core.lib.converters import scale, to_float
from pulse_core.lib.dates import parse_date
from pulse_core.lib.db import acquire, close_pool
from pulse_core.lib.tushare_client import get_pro_client, tushare_retry

from ._base import PROGRESS_INTERVAL, SLEEP_BETWEEN_CALLS, fetch_trading_days
from ._cli import IngestionArgs, parse_args

_UPSERT_SQL = """
INSERT INTO daily_cn (
    ts_code, trade_date, open, high, low, close, pre_close,
    change, pct_chg, vol, amount
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    pre_close = EXCLUDED.pre_close,
    change = EXCLUDED.change,
    pct_chg = EXCLUDED.pct_chg,
    vol = EXCLUDED.vol,
    amount = EXCLUDED.amount
"""


@tushare_retry
def _fetch_daily(trade_date: str) -> pd.DataFrame:
    """Fetch full-market daily OHLCV data for one trade date from Tushare."""
    pro = get_pro_client()
    return pro.daily(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert Tushare DataFrame to executemany rows."""
    rows: list[tuple] = []
    for r in df.itertuples(index=False):
        rows.append(
            (
                r.ts_code,
                parse_date(r.trade_date),
                to_float(r.open),
                to_float(r.high),
                to_float(r.low),
                to_float(r.close),
                to_float(r.pre_close),
                to_float(r.change),
                to_float(r.pct_chg),
                scale(to_float(r.vol), 100),
                scale(to_float(r.amount), 1000),
            )
        )
    return rows


async def _resolve_range(args: IngestionArgs) -> tuple[date, date]:
    """Resolve sync range from CLI override or DB incremental state."""
    end = args.end or date.today()
    if args.start:
        return args.start, end

    async with acquire() as conn:
        max_trade_date = await conn.fetchval("SELECT MAX(trade_date) FROM daily_cn")

    if max_trade_date is None:
        return HISTORY_START_DATE, end

    return max_trade_date + timedelta(days=1), end


async def sync_daily_cn(args: IngestionArgs) -> int:
    """Sync A-share daily OHLCV data into daily_cn."""
    start, end = await _resolve_range(args)
    logger.info(f"daily_cn sync range: {start} -> {end} (dry_run={args.dry_run})")

    if start > end:
        logger.info("Range is empty (start > end); nothing to do")
        return 0

    async with acquire() as conn:
        trading_days = await fetch_trading_days(conn, start, end)

    if not trading_days:
        logger.info("No trading days in range; nothing to do")
        return 0

    logger.info(f"Found {len(trading_days)} trading days")

    total = 0
    for i, trading_day in enumerate(trading_days, 1):
        trade_date = trading_day.strftime("%Y%m%d")
        df = _fetch_daily(trade_date)

        if df.empty:
            logger.warning(f"Empty daily data for {trading_day}; skipping")
            await asyncio.sleep(SLEEP_BETWEEN_CALLS)
            continue

        if args.dry_run:
            logger.info(f"DRY-RUN: would upsert {len(df)} rows for {trading_day}")
            total += len(df)
        else:
            rows = _df_to_rows(df)
            async with acquire() as conn, conn.transaction():
                await conn.executemany(_UPSERT_SQL, rows)
            logger.info(f"Upserted {len(rows)} rows for {trading_day}")
            total += len(rows)

        if i % PROGRESS_INTERVAL == 0 or i == len(trading_days):
            logger.info(f"Progress: {i}/{len(trading_days)} ({trading_day}) | total: {total}")

        await asyncio.sleep(SLEEP_BETWEEN_CALLS)

    logger.info(f"Done, total {total} rows {'(dry-run)' if args.dry_run else 'into daily_cn'}")
    return total


async def _main() -> None:
    args = parse_args("daily_cn")
    if args.stocks:
        logger.warning("--stocks ignored: daily_cn fetches full market per trade day")
    if args.limit:
        logger.warning("--limit ignored: daily_cn syncs by trade date range, not by count")
    try:
        await sync_daily_cn(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
