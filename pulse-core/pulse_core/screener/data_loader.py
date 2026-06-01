"""Stage 0:从 DB 加载 ScreenerData。

读取 7 张源表 → 装配 ScreenerData。失败抛异常 → Runner 整个 job FAIL(§7.3)。

历史窗口 lookback_days 由 Runner 从所有 Filter / Strategy 的 lookback 取最大值预算。
本期默认取 60 个交易日(覆盖 lookback=5 的 LowLiquidityFilter + 未来 lookback=20 策略)。
"""

from __future__ import annotations

from datetime import date, timedelta

import asyncpg
import pandas as pd

from pulse_core.lib.logger import logger
from pulse_core.screener.base import ScreenerData


async def load_screener_data(
    conn: asyncpg.Connection,
    trade_date: date,
    *,
    lookback_days: int = 60,
) -> ScreenerData:
    """加载指定交易日的 ScreenerData。

    Args:
        conn: asyncpg 连接(由 Runner 持有)。
        trade_date: 目标交易日。
        lookback_days: 历史窗口自然天数,覆盖所有 Filter/Strategy 最大 lookback。

    Returns:
        ScreenerData TypedDict;universe = 当日有 daily_cn 行的 ts_code(剔除停牌)。

    Raises:
        ValueError: 当日 daily_cn 为空(非交易日 / 数据未同步)。
    """
    history_start = trade_date - timedelta(days=lookback_days * 2)

    stocks_df = await _fetch_stocks(conn)
    daily_df = await _fetch_table_on_date(conn, "daily_cn", trade_date)
    if daily_df.empty:
        raise ValueError(
            f"daily_cn 在 {trade_date} 无数据 —— 非交易日或晚间同步未完成"
        )

    basic_df     = await _fetch_table_on_date(conn, "daily_basic_cn", trade_date)
    moneyflow_df = await _fetch_table_on_date(conn, "moneyflow_cn", trade_date)
    trend_df     = await _fetch_table_on_date(conn, "daily_trend_indicators_cn", trade_date)
    momentum_df  = await _fetch_table_on_date(conn, "daily_momentum_indicators_cn", trade_date)
    volume_df    = await _fetch_table_on_date(conn, "daily_volume_indicators_cn", trade_date)
    moneyflow_ind_df = await _fetch_table_on_date(
        conn, "daily_moneyflow_indicators_cn", trade_date,
    )

    history_df = await _fetch_history_window(conn, history_start, trade_date)

    universe = sorted(daily_df.index.tolist())

    logger.info(
        f"load_screener_data: trade_date={trade_date} "
        f"universe={len(universe)} stocks={len(stocks_df)} "
        f"history_rows={len(history_df)} (window={lookback_days}d)"
    )

    return ScreenerData(
        daily=daily_df,
        basic=basic_df,
        moneyflow=moneyflow_df,
        trend=trend_df,
        momentum=momentum_df,
        volume=volume_df,
        moneyflow_ind=moneyflow_ind_df,
        history=history_df,
        stocks=stocks_df,
        trade_date=trade_date,
        universe=universe,
    )


async def _fetch_stocks(conn: asyncpg.Connection) -> pd.DataFrame:
    """加载 stocks_cn 元数据,以 ts_code 为索引;仅保留未退市股票。"""
    rows = await conn.fetch(
        "SELECT ts_code, name, list_date, delist_date, industry "
        "FROM stocks_cn WHERE delist_date IS NULL"
    )
    df = pd.DataFrame(rows, columns=["ts_code", "name", "list_date", "delist_date", "industry"])
    if df.empty:
        return df.set_index("ts_code")
    return df.set_index("ts_code")


async def _fetch_table_on_date(
    conn: asyncpg.Connection,
    table: str,
    trade_date: date,
) -> pd.DataFrame:
    """加载某表在 trade_date 当日切片,以 ts_code 为索引。表名硬编码,无注入风险。"""
    rows = await conn.fetch(
        f"SELECT * FROM {table} WHERE trade_date = $1",  # noqa: S608
        trade_date,
    )
    if not rows:
        return pd.DataFrame().set_index(pd.Index([], name="ts_code"))
    df = pd.DataFrame(rows, columns=list(rows[0].keys()))
    return df.set_index("ts_code")


async def _fetch_history_window(
    conn: asyncpg.Connection,
    start: date,
    end: date,
) -> pd.DataFrame:
    """加载历史窗口。

    长表格式:(ts_code, trade_date) 双索引,按 ts_code 分组后 tail(N) 取最近 N 日。
    amount 来自 daily_cn(Tushare 原始 daily 接口);turnover_rate 来自 daily_basic_cn。
    """
    rows = await conn.fetch(
        """
        SELECT
            d.ts_code, d.trade_date,
            d.open, d.high, d.low, d.close, d.vol, d.pct_chg, d.amount,
            b.turnover_rate
        FROM daily_cn d
        LEFT JOIN daily_basic_cn b
            ON b.ts_code = d.ts_code AND b.trade_date = d.trade_date
        WHERE d.trade_date BETWEEN $1 AND $2
        ORDER BY d.ts_code, d.trade_date
        """,
        start, end,
    )
    if not rows:
        return pd.DataFrame().set_index(
            pd.MultiIndex.from_tuples([], names=["ts_code", "trade_date"])
        )
    df = pd.DataFrame(rows, columns=list(rows[0].keys()))
    return df.set_index(["ts_code", "trade_date"])
