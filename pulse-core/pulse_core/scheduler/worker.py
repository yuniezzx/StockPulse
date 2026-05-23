"""Worker 主循环：轮询 job_runs、执行 handler、写回执行结果。

整个系统中**只有** worker 会驱动 job_runs 的状态机：
pending → running → {success | failed | partial | skipped}。
"""

import asyncio
import traceback
from typing import Final

from loguru import logger

from pulse_core.lib.db import acquire
from pulse_core.lib.job_runs import (
    STATUS_FAILED,
    JobRun,
    fetch_and_lock_pending,
    mark_finished,
    mark_running,
)
from pulse_core.scheduler.registry import JobResult, Registry

_POLL_INTERVAL_SECONDS: Final = 1.0
_ERROR_MESSAGE_MAX_LEN: Final = 4000
_TRUNCATION_MARKER_TEMPLATE: Final = "\n...[truncated {dropped} chars]...\n"


def _truncate(s: str) -> str:
    """保留头尾、丢中间的截断策略。

    traceback 的关键信息在两端（最顶部是异常类型，最底部是最深的栈帧），
    只截头部会丢掉最有用的那一行，因此左右各保留一半预算。
    """
    if len(s) <= _ERROR_MESSAGE_MAX_LEN:
        return s
    marker = _TRUNCATION_MARKER_TEMPLATE.format(dropped=0)
    available = _ERROR_MESSAGE_MAX_LEN - len(marker)
    head_len = available // 2
    tail_len = available - head_len
    dropped = len(s) - head_len - tail_len
    return s[:head_len] + _TRUNCATION_MARKER_TEMPLATE.format(dropped=dropped) + s[-tail_len:]


async def _claim_one() -> JobRun | None:
    """事务内把下一行 pending 原子地推进到 running。"""
    async with acquire() as conn, conn.transaction():
        run = await fetch_and_lock_pending(conn)
        if run is None:
            return None
        ok = await mark_running(run.id, conn=conn)
        if not ok:
            return None
        return run


async def _execute(run: JobRun, registry: Registry) -> JobResult:
    """跑 handler；未捕获的异常统一兜底为 JobResult(status=failed)。"""
    handler = registry.get(run.job_name)
    if handler is None:
        return JobResult(
            status=STATUS_FAILED,
            error_message=f"unknown job: {run.job_name}",
        )
    try:
        return await handler(run)
    except Exception as e:
        tb = traceback.format_exc()
        logger.exception(f"[run_id={run.id}] handler raised")
        return JobResult(
            status=STATUS_FAILED,
            error_message=_truncate(f"{type(e).__name__}: {e}\n{tb}"),
        )


async def _record_result(run_id: int, result: JobResult) -> None:
    await mark_finished(
        run_id,
        result.status,
        rows_affected=result.rows_affected,
        error_message=result.error_message,
        details=result.details,
    )


async def _run_once(registry: Registry) -> bool:
    """处理至多一条 pending；返回是否真的干了活。"""
    run = await _claim_one()
    if run is None:
        return False
    logger.info(f"[run_id={run.id}] claimed job={run.job_name} source={run.trigger_source}")
    result = await _execute(run, registry)
    await _record_result(run.id, result)
    logger.info(f"[run_id={run.id}] finished status={result.status} rows={result.rows_affected}")
    return True


async def run_worker(stop_event: asyncio.Event, registry: Registry) -> None:
    """worker 主循环，直到 stop_event 被置位才退出。"""
    logger.info(
        f"worker started (poll_interval={_POLL_INTERVAL_SECONDS}s, "
        f"handlers={len(registry)})"
    )
    while not stop_event.is_set():
        try:
            had_work = await _run_once(registry)
        except Exception:
            logger.exception("worker loop iteration failed; sleeping before retry")
            had_work = False

        if had_work:
            continue

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=_POLL_INTERVAL_SECONDS)
        except TimeoutError:
            pass
    logger.info("worker stopped")
