"""派生指标计算 runner：一次性写入四张 daily_*_indicators_cn 表。

数据流：daily_cn + adj_factor_cn + daily_basic_cn + moneyflow_cn + stk_limit_cn
       → apply_qfq → compute_* → upsert 4 张目标表
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import asyncpg
import pandas as pd
from loguru import logger

from pulse_core.indicators import adjust, momentum, moneyflow, trend, volume
from pulse_core.ingestion._base import resolve_date_range
from pulse_core.ingestion._cli import IngestionArgs, parse_args
from pulse_core.lib.db import acquire, close_pool

_WARMUP_TRADING_DAYS = 60

_SOURCE_DAILY_SQL = """
SELECT ts_code, trade_date, open, high, low, close, vol, amount
FROM daily_cn
WHERE trade_date BETWEEN $1 AND $2
ORDER BY ts_code, trade_date
"""

_SOURCE_ADJ_SQL = """
SELECT ts_code, trade_date, adj_factor
FROM adj_factor_cn
WHERE trade_date BETWEEN $1 AND $2
ORDER BY ts_code, trade_date
"""

_SOURCE_BASIC_SQL = """
SELECT ts_code, trade_date, turnover_rate, pe_ttm, pb
FROM daily_basic_cn
WHERE trade_date BETWEEN $1 AND $2
ORDER BY ts_code, trade_date
"""

_SOURCE_MONEYFLOW_SQL = """
SELECT ts_code, trade_date, buy_sm_amount, sell_sm_amount, buy_md_amount, sell_md_amount,
       buy_lg_amount, sell_lg_amount, buy_elg_amount, sell_elg_amount
FROM moneyflow_cn
WHERE trade_date BETWEEN $1 AND $2
ORDER BY ts_code, trade_date
"""

_SOURCE_LIMIT_SQL = """
SELECT ts_code, trade_date, up_limit, down_limit
FROM stk_limit_cn
WHERE trade_date BETWEEN $1 AND $2
ORDER BY ts_code, trade_date
"""

_WARMUP_START_SQL = """
SELECT cal_date
FROM trade_cal_cn
WHERE exchange = 'SSE'
  AND is_open = 1
  AND cal_date < $1
ORDER BY cal_date DESC
OFFSET $2 LIMIT 1
"""

_UPSERT_TREND_SQL = """
INSERT INTO daily_trend_indicators_cn (
    ts_code, trade_date, ma5, ma10, ma20, ma60,
    ema12, ema26, dif, dea, hist,
    is_macd_golden_cross, is_ma_bull_arrangement
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    ma5 = EXCLUDED.ma5,
    ma10 = EXCLUDED.ma10,
    ma20 = EXCLUDED.ma20,
    ma60 = EXCLUDED.ma60,
    ema12 = EXCLUDED.ema12,
    ema26 = EXCLUDED.ema26,
    dif = EXCLUDED.dif,
    dea = EXCLUDED.dea,
    hist = EXCLUDED.hist,
    is_macd_golden_cross = EXCLUDED.is_macd_golden_cross,
    is_ma_bull_arrangement = EXCLUDED.is_ma_bull_arrangement
"""

_UPSERT_MOMENTUM_SQL = """
INSERT INTO daily_momentum_indicators_cn (
    ts_code, trade_date, rsi6, rsi12, rsi24, is_rsi_bull_arrangement,
    atr14, pct_chg_5d, pct_chg_20d, gap_pct, body_pct,
    is_new_high_60d, is_new_low_60d, is_limit_up, is_limit_down
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    rsi6 = EXCLUDED.rsi6,
    rsi12 = EXCLUDED.rsi12,
    rsi24 = EXCLUDED.rsi24,
    is_rsi_bull_arrangement = EXCLUDED.is_rsi_bull_arrangement,
    atr14 = EXCLUDED.atr14,
    pct_chg_5d = EXCLUDED.pct_chg_5d,
    pct_chg_20d = EXCLUDED.pct_chg_20d,
    gap_pct = EXCLUDED.gap_pct,
    body_pct = EXCLUDED.body_pct,
    is_new_high_60d = EXCLUDED.is_new_high_60d,
    is_new_low_60d = EXCLUDED.is_new_low_60d,
    is_limit_up = EXCLUDED.is_limit_up,
    is_limit_down = EXCLUDED.is_limit_down
"""

_UPSERT_VOLUME_SQL = """
INSERT INTO daily_volume_indicators_cn (
    ts_code, trade_date, vol_ma5, vol_ma10, vol_ratio_5,
    turnover_rate_ma5, turnover_rate_ratio_5, pe_ttm_pct_60, pb_pct_60
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    vol_ma5 = EXCLUDED.vol_ma5,
    vol_ma10 = EXCLUDED.vol_ma10,
    vol_ratio_5 = EXCLUDED.vol_ratio_5,
    turnover_rate_ma5 = EXCLUDED.turnover_rate_ma5,
    turnover_rate_ratio_5 = EXCLUDED.turnover_rate_ratio_5,
    pe_ttm_pct_60 = EXCLUDED.pe_ttm_pct_60,
    pb_pct_60 = EXCLUDED.pb_pct_60
"""

_UPSERT_MONEYFLOW_SQL = """
INSERT INTO daily_moneyflow_indicators_cn (
    ts_code, trade_date, main_net_amount, main_net_ratio, main_net_amount_ma5,
    retail_net_amount
) VALUES (
    $1, $2, $3, $4, $5, $6
) ON CONFLICT (ts_code, trade_date) DO UPDATE SET
    main_net_amount = EXCLUDED.main_net_amount,
    main_net_ratio = EXCLUDED.main_net_ratio,
    main_net_amount_ma5 = EXCLUDED.main_net_amount_ma5,
    retail_net_amount = EXCLUDED.retail_net_amount
"""

_TREND_COLUMNS = [
    "ts_code",
    "trade_date",
    "ma5",
    "ma10",
    "ma20",
    "ma60",
    "ema12",
    "ema26",
    "dif",
    "dea",
    "hist",
    "is_macd_golden_cross",
    "is_ma_bull_arrangement",
]
_MOMENTUM_COLUMNS = [
    "ts_code",
    "trade_date",
    "rsi6",
    "rsi12",
    "rsi24",
    "is_rsi_bull_arrangement",
    "atr14",
    "pct_chg_5d",
    "pct_chg_20d",
    "gap_pct",
    "body_pct",
    "is_new_high_60d",
    "is_new_low_60d",
    "is_limit_up",
    "is_limit_down",
]
_VOLUME_COLUMNS = [
    "ts_code",
    "trade_date",
    "vol_ma5",
    "vol_ma10",
    "vol_ratio_5",
    "turnover_rate_ma5",
    "turnover_rate_ratio_5",
    "pe_ttm_pct_60",
    "pb_pct_60",
]
_MONEYFLOW_COLUMNS = [
    "ts_code",
    "trade_date",
    "main_net_amount",
    "main_net_ratio",
    "main_net_amount_ma5",
    "retail_net_amount",
]


async def _load_source_data(
    conn: asyncpg.Connection,
    start: date,
    end: date,
) -> dict[str, pd.DataFrame]:
    """Load source tables with a 60 trading day warmup window."""
    warmup_start = await conn.fetchval(_WARMUP_START_SQL, start, _WARMUP_TRADING_DAYS - 1)
    window_start = warmup_start or start
    rows = {
        "daily": await conn.fetch(_SOURCE_DAILY_SQL, window_start, end),
        "adj": await conn.fetch(_SOURCE_ADJ_SQL, window_start, end),
        "basic": await conn.fetch(_SOURCE_BASIC_SQL, window_start, end),
        "mf": await conn.fetch(_SOURCE_MONEYFLOW_SQL, window_start, end),
        "limits": await conn.fetch(_SOURCE_LIMIT_SQL, window_start, end),
    }
    return {name: pd.DataFrame.from_records(records) for name, records in rows.items()}


def _compute_all_indicators(
    daily: pd.DataFrame,
    adj: pd.DataFrame,
    basic: pd.DataFrame,
    mf: pd.DataFrame,
    limits: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Compute all four daily indicator tables from source DataFrames."""
    qfq = adjust.apply_qfq(daily, adj)

    trend_df = qfq[["ts_code", "trade_date", "close_qfq"]].copy()
    trend_df = trend.compute_ma(trend_df)
    trend_df = trend.compute_ema(trend_df)
    trend_df = trend.compute_macd(trend_df)

    momentum_df = qfq[
        ["ts_code", "trade_date", "open_qfq", "high_qfq", "low_qfq", "close_qfq"]
    ].copy()
    momentum_df = momentum.compute_rsi(momentum_df)
    momentum_df = momentum.compute_atr(momentum_df)
    momentum_df = momentum.compute_pct_chg(momentum_df)
    momentum_df = momentum.compute_candle_shape(momentum_df)
    momentum_df = momentum.compute_new_high_low(momentum_df)
    momentum_with_limits = momentum_df.merge(
        daily[["ts_code", "trade_date", "close"]],
        on=["ts_code", "trade_date"],
    ).merge(
        limits[["ts_code", "trade_date", "up_limit", "down_limit"]],
        on=["ts_code", "trade_date"],
        how="left",
    )
    momentum_with_limits = momentum.compute_limit_flags(momentum_with_limits)
    momentum_df = momentum_df.merge(
        momentum_with_limits[["ts_code", "trade_date", "is_limit_up", "is_limit_down"]],
        on=["ts_code", "trade_date"],
    )

    volume_df = qfq[["ts_code", "trade_date", "vol"]].copy()
    volume_df = volume.compute_vol_ma(volume_df)
    volume_with_basic = volume_df.merge(
        basic[["ts_code", "trade_date", "turnover_rate", "pe_ttm", "pb"]],
        on=["ts_code", "trade_date"],
        how="left",
    )
    volume_with_basic = volume.compute_turnover_ratio(volume_with_basic)
    volume_with_basic = volume.compute_pe_pb_quantile(volume_with_basic)
    volume_final = volume_with_basic.dropna(subset=["turnover_rate", "pe_ttm", "pb"], how="all")

    mf_with_amount = mf.merge(
        daily[["ts_code", "trade_date", "amount"]],
        on=["ts_code", "trade_date"],
        how="inner",
    )
    mf_df = moneyflow.compute_main_net(mf_with_amount)
    mf_df = moneyflow.compute_retail_net(mf_df)

    return {
        "daily_trend_indicators_cn": trend_df[_TREND_COLUMNS],
        "daily_momentum_indicators_cn": momentum_df[_MOMENTUM_COLUMNS],
        "daily_volume_indicators_cn": volume_final[_VOLUME_COLUMNS],
        "daily_moneyflow_indicators_cn": mf_df[_MONEYFLOW_COLUMNS],
    }


def _df_to_rows(df: pd.DataFrame) -> list[tuple]:
    """Convert pandas rows to asyncpg-compatible tuples."""
    rows: list[tuple] = []
    for row in df.itertuples(index=False, name=None):
        converted: list[Any] = []
        for value in row:
            if pd.isna(value):
                converted.append(None)
            elif isinstance(value, bool):
                converted.append(bool(value))
            elif hasattr(value, "item"):
                converted.append(value.item())
            else:
                converted.append(value)
        rows.append(tuple(converted))
    return rows


async def sync_daily_indicators_cn(args: IngestionArgs) -> int:
    """计算并写入 4 张派生指标表。"""
    async with acquire() as conn:
        start, end = await resolve_date_range(
            conn, "daily_trend_indicators_cn", args.start, args.end
        )
        sources = await _load_source_data(conn, start, end)

    if sources["daily"].empty:
        logger.info("no daily_cn data in window, skipping")
        return 0

    indicators = _compute_all_indicators(**sources)
    for table_name, df in indicators.items():
        indicators[table_name] = df[df["trade_date"] >= start]

    if args.dry_run:
        logger.info("dry-run: skipping upsert")
        return sum(len(df) for df in indicators.values())

    total_rows = 0
    async with acquire() as conn, conn.transaction():
        for sql, df in [
            (_UPSERT_TREND_SQL, indicators["daily_trend_indicators_cn"]),
            (_UPSERT_MOMENTUM_SQL, indicators["daily_momentum_indicators_cn"]),
            (_UPSERT_VOLUME_SQL, indicators["daily_volume_indicators_cn"]),
            (_UPSERT_MONEYFLOW_SQL, indicators["daily_moneyflow_indicators_cn"]),
        ]:
            rows = _df_to_rows(df)
            if rows:
                await conn.executemany(sql, rows)
            total_rows += len(rows)

    logger.info(f"daily_indicators upserted total {total_rows} rows across 4 tables")
    return total_rows


async def _main() -> None:
    args = parse_args("daily_indicators")
    try:
        await sync_daily_indicators_cn(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
