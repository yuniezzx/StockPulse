"""数据同步 (ingestion) job handler 集合。

每个 handler 都遵循 registry 合同：
  async def(run: JobRun) -> JobResult

handler 内部**不吞**意外异常，由 worker 兜底为 failed。
evening_ingestion 内部容忍单个子任务失败：至少一个失败、至少一个成功 → partial。
"""

from collections.abc import Awaitable, Callable

from loguru import logger

from pulse_core.ingestion._cli import IngestionArgs
from pulse_core.ingestion.adj_factor_cn import sync_adj_factor_cn
from pulse_core.ingestion.daily_basic_cn import sync_daily_basic_cn
from pulse_core.ingestion.daily_cn import sync_daily_cn
from pulse_core.ingestion.moneyflow_cn import sync_moneyflow_cn
from pulse_core.ingestion.stk_limit_cn import sync_stk_limit_cn
from pulse_core.ingestion.stocks_cn import sync_stocks_cn
from pulse_core.ingestion.trade_cal_cn import sync_trade_cal_cn
from pulse_core.lib.job_runs import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    JobRun,
)
from pulse_core.scheduler.registry import JobResult

AsyncSync = Callable[[IngestionArgs], Awaitable[int]]


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
    """串行跑 5 个日终同步子任务，允许部分失败。"""
    args = IngestionArgs()
    pipeline: list[tuple[str, AsyncSync]] = [
        ("daily_cn", sync_daily_cn),
        ("adj_factor_cn", sync_adj_factor_cn),
        ("stk_limit_cn", sync_stk_limit_cn),
        ("daily_basic_cn", sync_daily_basic_cn),
        ("moneyflow_cn", sync_moneyflow_cn),
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
