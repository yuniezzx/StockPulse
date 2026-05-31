"""Shared helpers for daily-cadence Tushare ingestion.

负责"增量同步窗口"的计算：
- 决定本次同步的起止日期（首次全量 / 增量回看 N 个交易日防漏）
- 查询交易日列表

Tushare 限流相关常量（SLEEP_BETWEEN_CALLS / PROGRESS_INTERVAL）也放在这里，
所有 ingestion 脚本统一引用，避免每个脚本写死自己的节奏。
"""

from datetime import date

from loguru import logger

from pulse_core.lib.config import HISTORY_START_DATE

# --- 速率与进度 ---
SLEEP_BETWEEN_CALLS = 0.5  # 调用方在循环里 await asyncio.sleep(SLEEP_BETWEEN_CALLS)
PROGRESS_INTERVAL = 50  # 每 N 步打一次进度日志

# --- 增量回看 ---
LOOKBACK_TRADING_DAYS = 3
# 增量同步时，从最新已入库日期往回多覆盖 3 个交易日。
# 目的：覆盖 Tushare 当天数据延迟修正（个股停复牌、价格修正等）。

# --- SQL ---
TRADING_DAYS_SQL = """
SELECT cal_date FROM trade_cal_cn
WHERE exchange = 'SSE'
  AND is_open = 1
  AND cal_date BETWEEN $1 AND $2
ORDER BY cal_date
"""

LOOKBACK_START_SQL = """
SELECT cal_date FROM trade_cal_cn
WHERE exchange = 'SSE'
  AND is_open = 1
  AND cal_date <= $1
ORDER BY cal_date DESC
OFFSET $2 LIMIT 1
"""


async def resolve_date_range(
    conn,
    table_name: str,
    cli_start: date | None = None,
    cli_end: date | None = None,
) -> tuple[date, date]:
    """Determine [start, end] sync window for a daily table.

    优先级：
    1. CLI 参数（cli_start / cli_end）— 测试模式，完全覆盖
    2. DB 增量推断：
       - 表为空 → start = HISTORY_START_DATE（全量首次同步）
       - 表已有数据 → start = 最新 trade_date 往回 LOOKBACK_TRADING_DAYS - 1 个交易日
    3. end 默认今天
    """
    if cli_start or cli_end:
        start = cli_start or HISTORY_START_DATE
        end = cli_end or date.today()
        logger.info(f"CLI override range for {table_name}: {start} -> {end}")
        return start, end

    last = await conn.fetchval(f"SELECT MAX(trade_date) FROM {table_name}")
    if last is None:
        start = HISTORY_START_DATE
        logger.info(f"Empty {table_name} table; full sync from {start}")
    else:
        start = await conn.fetchval(LOOKBACK_START_SQL, last, LOOKBACK_TRADING_DAYS - 1)
        start = start or last
        logger.info(
            f"Incremental sync from {start} "
            f"(last={last}, lookback={LOOKBACK_TRADING_DAYS} trading days)"
        )
    return start, date.today()


async def fetch_trading_days(conn, start: date, end: date) -> list[date]:
    """Return list of trading days in [start, end] from trade_cal_cn (SSE)."""
    rows = await conn.fetch(TRADING_DAYS_SQL, start, end)
    return [r["cal_date"] for r in rows]
