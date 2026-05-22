"""Scheduler job wrappers for pulse-core ingestion tasks.

APScheduler 调用的同步入口函数；内部桥接到现有 async ingestion。
每个 job 跑完必须 close_pool()，防连接泄漏。
"""

import asyncio
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
from pulse_core.lib.db import close_pool

AsyncSync = Callable[[IngestionArgs], Awaitable[int]]


def _run_single(job_name: str, sync_fn: AsyncSync) -> int:
    """Run one async ingestion job in sync APScheduler context."""

    async def _runner() -> int:
        try:
            logger.info(f"Starting job: {job_name}")
            rows = await sync_fn(IngestionArgs())
            logger.info(f"Finished job: {job_name} (rows={rows})")
            return rows
        finally:
            await close_pool()

    return asyncio.run(_runner())


def sync_trade_cal_cn_job() -> int:
    """Monthly trade_cal_cn sync (1st of each month, 18:00)."""
    return _run_single("trade_cal_cn_monthly", sync_trade_cal_cn)


def sync_stocks_cn_job() -> int:
    """Weekly stocks_cn sync (Sunday 18:00)."""
    return _run_single("stocks_cn_weekly", sync_stocks_cn)


def run_evening_ingestion() -> None:
    """Run evening ingestion pipeline serially.

    串行执行 5 个日更 ingestion；单个失败仅记日志，不阻断后续任务。
    """
    # TODO: 后续接入 trade_cal_cn 判断，非交易日时直接跳过。

    async def _runner() -> None:
        args = IngestionArgs()
        pipeline: list[tuple[str, AsyncSync]] = [
            ("daily_cn", sync_daily_cn),
            ("adj_factor_cn", sync_adj_factor_cn),
            ("stk_limit_cn", sync_stk_limit_cn),
            ("daily_basic_cn", sync_daily_basic_cn),
            ("moneyflow_cn", sync_moneyflow_cn),
        ]
        success: list[str] = []
        failed: list[str] = []

        logger.info("Starting evening_ingestion pipeline")
        try:
            for job_name, sync_fn in pipeline:
                try:
                    rows = await sync_fn(args)
                    success.append(job_name)
                    logger.info(f"{job_name} OK (rows={rows})")
                except Exception:
                    failed.append(job_name)
                    logger.exception(f"{job_name} failed")

            logger.info(
                f"evening_ingestion done: success={len(success)} failed={len(failed)} "
                f"failed_jobs={failed}"
            )
        finally:
            await close_pool()

    asyncio.run(_runner())


def run_screener_placeholder() -> None:
    """Placeholder for future screener.runner."""
    # TODO: 后续接入 trade_cal_cn 判断 + 替换为真实 screener.runner 调用。
    logger.warning("screener.runner 尚未实现，跳过")
