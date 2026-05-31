"""数据同步 (ingestion) job handler 集合。

每个 handler 都遵循 registry 合同：
  async def(run: JobRun) -> JobResult

handler 内部**不吞**意外异常，由 worker 兜底为 failed。
evening_ingestion 内部容忍单个子任务失败：至少一个失败、至少一个成功 → partial。
"""

from collections.abc import Awaitable, Callable
from datetime import datetime

from loguru import logger

from pulse_core.indicators.runner import sync_daily_indicators_cn
from pulse_core.ingestion._cli import IngestionArgs
from pulse_core.ingestion.adj_factor_cn import sync_adj_factor_cn
from pulse_core.ingestion.daily_basic_cn import sync_daily_basic_cn
from pulse_core.ingestion.daily_cn import sync_daily_cn
from pulse_core.ingestion.moneyflow_cn import sync_moneyflow_cn
from pulse_core.ingestion.stk_limit_cn import sync_stk_limit_cn
from pulse_core.ingestion.stocks_cn import sync_stocks_cn
from pulse_core.ingestion.trade_cal_cn import sync_trade_cal_cn
from pulse_core.lib.db import acquire
from pulse_core.lib.job_runs import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
    JobRun,
)
from pulse_core.scheduler.registry import JobResult

AsyncSync = Callable[[IngestionArgs], Awaitable[int]]

# 交易日历用上交所（SSE）作为权威：沪深两市交易日完全一致，
# 任选其一查询即可，避免双表 join。
_CALENDAR_EXCHANGE = "SSE"

_IS_TRADING_DAY_SQL = """
SELECT is_open
FROM trade_cal_cn
WHERE exchange = $1 AND cal_date = $2
"""


async def _is_trading_day(date_: datetime) -> bool | None:
    """查 trade_cal_cn 判断给定日期是否交易日。

    返回值：
      True  → 交易日
      False → 非交易日（周末 / 节假日 / 调休休市）
      None  → 该日历日在 trade_cal_cn 中不存在（日历未同步到该日期）
              调用方应当作"未知"处理，保守选择继续执行 + 告警。
    """
    async with acquire() as conn:
        is_open = await conn.fetchval(_IS_TRADING_DAY_SQL, _CALENDAR_EXCHANGE, date_.date())
    if is_open is None:
        return None
    return is_open == 1


async def sync_trade_cal_cn_handler(run: JobRun) -> JobResult:
    """同步当期交易日历 (trade_cal_cn)。"""
    logger.info(f"[run_id={run.id}] starting sync_trade_cal_cn")
    rows = await sync_trade_cal_cn(IngestionArgs())
    logger.info(f"[run_id={run.id}] sync_trade_cal_cn OK (rows={rows})")
    return JobResult(status=STATUS_SUCCESS, rows_affected=rows)


async def sync_stocks_cn_handler(run: JobRun) -> JobResult:
    """同步 A 股股票列表。"""
    logger.info(f"[run_id={run.id}] starting sync_stocks_cn")
    rows = await sync_stocks_cn(IngestionArgs())
    logger.info(f"[run_id={run.id}] sync_stocks_cn OK (rows={rows})")
    return JobResult(status=STATUS_SUCCESS, rows_affected=rows)


async def evening_ingestion_handler(run: JobRun) -> JobResult:
    """串行跑 5 个日终同步子任务，允许部分失败。

    非交易日（周末 / 节假日 / 调休休市）跳过整个 pipeline 并返回 status='skipped'，
    避免对 Tushare 发起注定拿空数据的调用、并避免在 job_runs 留 failed/partial 噪声。
    日历未覆盖到 run.scheduled_at 的日期时，**保守继续执行**（不静默跳过，
    便于通过 partial/failed 状态暴露"日历该补了"这个运维问题）。
    """
    trading = await _is_trading_day(run.scheduled_at)
    if trading is False:
        logger.info(f"[run_id={run.id}] {run.scheduled_at.date()} 非交易日，跳过 evening_ingestion")
        return JobResult(
            status=STATUS_SKIPPED,
            details={"reason": "non_trading_day", "date": run.scheduled_at.date().isoformat()},
        )
    if trading is None:
        logger.warning(
            f"[run_id={run.id}] {run.scheduled_at.date()} 不在 trade_cal_cn 覆盖范围内，"
            "继续执行（请尽快同步交易日历）"
        )

    args = IngestionArgs()
    pipeline: list[tuple[str, AsyncSync]] = [
        ("daily_cn", sync_daily_cn),
        ("adj_factor_cn", sync_adj_factor_cn),
        ("stk_limit_cn", sync_stk_limit_cn),
        ("daily_basic_cn", sync_daily_basic_cn),
        ("moneyflow_cn", sync_moneyflow_cn),
        ("daily_indicators", sync_daily_indicators_cn),
    ]
    success: dict[str, int] = {}
    failed: dict[str, str] = {}

    logger.info(f"[run_id={run.id}] starting evening_ingestion ({len(pipeline)} sub-tasks)")
    for sub_name, sync_fn in pipeline:
        try:
            rows = await sync_fn(args)
            success[sub_name] = rows
            logger.info(f"[run_id={run.id}] {sub_name} OK (rows={rows})")
        except Exception as e:
            failed[sub_name] = str(e)
            logger.exception(f"[run_id={run.id}] {sub_name} failed")

    total_rows = sum(success.values())
    details: dict[str, dict[str, int] | dict[str, str]] = {
        "success": success,
        "failed": failed,
    }

    if not failed:
        logger.info(f"[run_id={run.id}] evening_ingestion done: success={len(success)}")
        return JobResult(
            status=STATUS_SUCCESS,
            rows_affected=total_rows,
            details=details,
        )

    if success:
        logger.warning(
            f"[run_id={run.id}] evening_ingestion partial: "
            f"success={len(success)} failed={len(failed)} ({list(failed)})"
        )
        return JobResult(
            status=STATUS_PARTIAL,
            rows_affected=total_rows,
            details=details,
            error_message=f"{len(failed)} sub-task(s) failed: {list(failed)}",
        )

    logger.error(f"[run_id={run.id}] evening_ingestion all failed ({list(failed)})")
    return JobResult(
        status=STATUS_FAILED,
        rows_affected=0,
        details=details,
        error_message=f"all sub-tasks failed: {list(failed)}",
    )
