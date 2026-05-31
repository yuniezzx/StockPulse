"""Ingest A-share daily basic metrics (valuation/turnover/market cap) from Tushare.

默认行为：增量同步日度基础指标。
- 表为空：HISTORY_START_DATE -> today
- 表非空：MAX(trade_date) 回看 3 个交易日后 -> today

单位转换：
- 股本类（total_share/float_share/free_share）：万股 × 10000 → 股
- 市值类（total_mv/circ_mv）：万元 × 10000 → 元
- 其余比率/价格字段保留原值

支持 CLI 参数：--start / --end / --dry-run（--stocks / --limit 对按日全市场接口无意义，会被忽略）

用法:
    # 增量同步（默认）
    uv run python -m pulse_core.ingestion.daily_basic_cn

    # 限定范围 dry-run
    uv run python -m pulse_core.ingestion.daily_basic_cn --start 20260520 --end 20260520 --dry-run
"""

import asyncio

import pandas as pd
from loguru import logger

from pulse_core.lib.converters import scale, to_float
from pulse_core.lib.dates import parse_date
from pulse_core.lib.db import acquire, close_pool
from pulse_core.lib.tushare_client import get_pro_client, tushare_retry

from ._base import PROGRESS_INTERVAL, SLEEP_BETWEEN_CALLS, fetch_trading_days, resolve_date_range
from ._cli import IngestionArgs, parse_args

_UPSERT_SQL = """
INSERT INTO daily_basic_cn (
    ts_code, trade_date, close,
    turnover_rate, turnover_rate_f, volume_ratio,
    pe, pe_ttm, pb, ps, ps_ttm,
    dv_ratio, dv_ttm,
    total_share, float_share, free_share,
    total_mv, circ_mv
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
    $11, $12, $13, $14, $15, $16, $17, $18
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    close = EXCLUDED.close,
    turnover_rate = EXCLUDED.turnover_rate,
    turnover_rate_f = EXCLUDED.turnover_rate_f,
    volume_ratio = EXCLUDED.volume_ratio,
    pe = EXCLUDED.pe,
    pe_ttm = EXCLUDED.pe_ttm,
    pb = EXCLUDED.pb,
    ps = EXCLUDED.ps,
    ps_ttm = EXCLUDED.ps_ttm,
    dv_ratio = EXCLUDED.dv_ratio,
    dv_ttm = EXCLUDED.dv_ttm,
    total_share = EXCLUDED.total_share,
    float_share = EXCLUDED.float_share,
    free_share = EXCLUDED.free_share,
    total_mv = EXCLUDED.total_mv,
    circ_mv = EXCLUDED.circ_mv
"""


@tushare_retry
def _fetch_daily_basic(trade_date: str) -> pd.DataFrame:
    """Fetch full-market daily basic metrics for one trade date from Tushare."""
    pro = get_pro_client()
    return pro.daily_basic(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert Tushare DataFrame to executemany rows.

    单位转换：股本类 × 10000 → 股；市值类 × 10000 → 元。
    其他字段（价格、比率）保留原值。所有业务字段都允许 NULL。
    """
    rows: list[tuple] = []
    for r in df.itertuples(index=False):
        rows.append(
            (
                r.ts_code,
                parse_date(r.trade_date),
                to_float(r.close),
                to_float(r.turnover_rate),
                to_float(r.turnover_rate_f),
                to_float(r.volume_ratio),
                to_float(r.pe),
                to_float(r.pe_ttm),
                to_float(r.pb),
                to_float(r.ps),
                to_float(r.ps_ttm),
                to_float(r.dv_ratio),
                to_float(r.dv_ttm),
                scale(to_float(r.total_share), 10000),
                scale(to_float(r.float_share), 10000),
                scale(to_float(r.free_share), 10000),
                scale(to_float(r.total_mv), 10000),
                scale(to_float(r.circ_mv), 10000),
            )
        )
    return rows


async def sync_daily_basic_cn(args: IngestionArgs) -> int:
    """Sync A-share daily basic metrics into daily_basic_cn."""
    async with acquire() as conn:
        start, end = await resolve_date_range(conn, "daily_basic_cn", args.start, args.end)
        trading_days = await fetch_trading_days(conn, start, end)

    logger.info(f"daily_basic_cn sync range: {start} -> {end} (dry_run={args.dry_run})")

    if not trading_days:
        logger.info("No trading days in range; nothing to do")
        return 0

    logger.info(f"Found {len(trading_days)} trading days")

    total = 0
    for i, trading_day in enumerate(trading_days, 1):
        trade_date = trading_day.strftime("%Y%m%d")
        df = _fetch_daily_basic(trade_date)

        if df.empty:
            logger.warning(f"Empty daily_basic data for {trading_day}; skipping")
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

    suffix = "(dry-run)" if args.dry_run else "into daily_basic_cn"
    logger.info(f"Done, total {total} rows {suffix}")
    return total


async def _main() -> None:
    args = parse_args("daily_basic_cn")
    if args.stocks:
        logger.warning("--stocks ignored: daily_basic_cn fetches full market per trade day")
    if args.limit:
        logger.warning("--limit ignored: daily_basic_cn syncs by trade date range, not by count")
    try:
        await sync_daily_basic_cn(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
