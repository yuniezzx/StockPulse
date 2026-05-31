"""Ingest A-share individual stock money flow from Tushare into moneyflow_cn.

默认行为：增量同步日度资金流向。
- 表为空：HISTORY_START_DATE -> today
- 表非空：MAX(trade_date) 回看 3 个交易日后 -> today

单位转换：
- vol 类（*_vol / net_mf_vol）：手 × 100 → 股
- amount 类（*_amount / net_mf_amount）：万元 × 10000 → 元

支持 CLI 参数：--start / --end / --dry-run（--stocks / --limit 对按日全市场接口无意义，会被忽略）

用法:
    # 增量同步（默认）
    uv run python -m pulse_core.ingestion.moneyflow_cn

    # 限定范围 dry-run
    uv run python -m pulse_core.ingestion.moneyflow_cn --start 20260520 --end 20260520 --dry-run
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
INSERT INTO moneyflow_cn (
    ts_code, trade_date,
    buy_sm_vol, buy_sm_amount, sell_sm_vol, sell_sm_amount,
    buy_md_vol, buy_md_amount, sell_md_vol, sell_md_amount,
    buy_lg_vol, buy_lg_amount, sell_lg_vol, sell_lg_amount,
    buy_elg_vol, buy_elg_amount, sell_elg_vol, sell_elg_amount,
    net_mf_vol, net_mf_amount
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    buy_sm_vol = EXCLUDED.buy_sm_vol,
    buy_sm_amount = EXCLUDED.buy_sm_amount,
    sell_sm_vol = EXCLUDED.sell_sm_vol,
    sell_sm_amount = EXCLUDED.sell_sm_amount,
    buy_md_vol = EXCLUDED.buy_md_vol,
    buy_md_amount = EXCLUDED.buy_md_amount,
    sell_md_vol = EXCLUDED.sell_md_vol,
    sell_md_amount = EXCLUDED.sell_md_amount,
    buy_lg_vol = EXCLUDED.buy_lg_vol,
    buy_lg_amount = EXCLUDED.buy_lg_amount,
    sell_lg_vol = EXCLUDED.sell_lg_vol,
    sell_lg_amount = EXCLUDED.sell_lg_amount,
    buy_elg_vol = EXCLUDED.buy_elg_vol,
    buy_elg_amount = EXCLUDED.buy_elg_amount,
    sell_elg_vol = EXCLUDED.sell_elg_vol,
    sell_elg_amount = EXCLUDED.sell_elg_amount,
    net_mf_vol = EXCLUDED.net_mf_vol,
    net_mf_amount = EXCLUDED.net_mf_amount
"""


@tushare_retry
def _fetch_moneyflow(trade_date: str) -> pd.DataFrame:
    """Fetch full-market daily money flow data for one trade date from Tushare."""
    pro = get_pro_client()
    return pro.moneyflow(trade_date=trade_date)


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert Tushare DataFrame to executemany rows.

    单位转换：vol 类 × 100（手 → 股）；amount 类 × 10000（万元 → 元）。
    所有业务字段允许 NULL。
    """
    rows: list[tuple] = []
    for r in df.itertuples(index=False):
        rows.append(
            (
                r.ts_code,
                parse_date(r.trade_date),
                scale(to_float(r.buy_sm_vol), 100),
                scale(to_float(r.buy_sm_amount), 10000),
                scale(to_float(r.sell_sm_vol), 100),
                scale(to_float(r.sell_sm_amount), 10000),
                scale(to_float(r.buy_md_vol), 100),
                scale(to_float(r.buy_md_amount), 10000),
                scale(to_float(r.sell_md_vol), 100),
                scale(to_float(r.sell_md_amount), 10000),
                scale(to_float(r.buy_lg_vol), 100),
                scale(to_float(r.buy_lg_amount), 10000),
                scale(to_float(r.sell_lg_vol), 100),
                scale(to_float(r.sell_lg_amount), 10000),
                scale(to_float(r.buy_elg_vol), 100),
                scale(to_float(r.buy_elg_amount), 10000),
                scale(to_float(r.sell_elg_vol), 100),
                scale(to_float(r.sell_elg_amount), 10000),
                scale(to_float(r.net_mf_vol), 100),
                scale(to_float(r.net_mf_amount), 10000),
            )
        )
    return rows


async def sync_moneyflow_cn(args: IngestionArgs) -> int:
    """Sync A-share daily money flow data into moneyflow_cn."""
    async with acquire() as conn:
        start, end = await resolve_date_range(conn, "moneyflow_cn", args.start, args.end)
        trading_days = await fetch_trading_days(conn, start, end)

    logger.info(f"moneyflow_cn sync range: {start} -> {end} (dry_run={args.dry_run})")

    if not trading_days:
        logger.info("No trading days in range; nothing to do")
        return 0

    logger.info(f"Found {len(trading_days)} trading days")

    total = 0
    for i, trading_day in enumerate(trading_days, 1):
        trade_date = trading_day.strftime("%Y%m%d")
        df = _fetch_moneyflow(trade_date)

        if df.empty:
            logger.warning(f"Empty moneyflow data for {trading_day}; skipping")
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

    suffix = "(dry-run)" if args.dry_run else "into moneyflow_cn"
    logger.info(f"Done, total {total} rows {suffix}")
    return total


async def _main() -> None:
    args = parse_args("moneyflow_cn")
    if args.stocks:
        logger.warning("--stocks ignored: moneyflow_cn fetches full market per trade day")
    if args.limit:
        logger.warning("--limit ignored: moneyflow_cn syncs by trade date range, not by count")
    try:
        await sync_moneyflow_cn(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
