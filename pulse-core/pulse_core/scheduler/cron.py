"""Cron 调度器：到点触发并往 job_runs 写 pending 行。

调度器**不执行业务逻辑**，只负责写 pending 行；真正干活的是 worker。
这种"写表 + 轮询"的拆分换来三样东西：可观测性、手动重跑能力、崩溃安全。

Cron 入队是幂等的：APScheduler 错过补发 / daemon 重启都不会重复入队，
由 job_runs 表上 (job_name, scheduled_at) 的部分唯一索引兜底。
"""

from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from pulse_core.lib.job_runs import enqueue_cron

TZ: Final = ZoneInfo("Asia/Shanghai")


async def _enqueue(job_name: str, fire_time: datetime) -> None:
    run_id = await enqueue_cron(job_name, fire_time)
    if run_id is None:
        logger.info(f"[cron] {job_name} @ {fire_time.isoformat()} already enqueued, skip")
    else:
        logger.info(f"[cron] {job_name} @ {fire_time.isoformat()} enqueued (run_id={run_id})")


async def _fire_sync_trade_cal_cn() -> None:
    await _enqueue("sync_trade_cal_cn", datetime.now(tz=TZ).replace(microsecond=0))


async def _fire_sync_stocks_cn() -> None:
    await _enqueue("sync_stocks_cn", datetime.now(tz=TZ).replace(microsecond=0))


async def _fire_evening_ingestion() -> None:
    await _enqueue("evening_ingestion", datetime.now(tz=TZ).replace(microsecond=0))


async def _fire_screener_runner() -> None:
    await _enqueue("screener_runner", datetime.now(tz=TZ).replace(microsecond=0))


def build_scheduler() -> AsyncIOScheduler:
    """构造并注册所有 cron 任务的 AsyncIOScheduler。"""
    scheduler = AsyncIOScheduler(timezone=TZ)

    scheduler.add_job(
        _fire_sync_trade_cal_cn,
        CronTrigger(hour=18, minute=0, timezone=TZ),
        id="cron_sync_trade_cal_cn",
        name="sync_trade_cal_cn @ 18:00 daily",
        misfire_grace_time=3600,
    )

    # 故意错开到 18:02 而不是 18:00：避免与 sync_trade_cal_cn 写出 scheduled_at
    # 完全相同的两行 job_runs，否则 worker 的 ORDER BY scheduled_at 会出现
    # 未定义的平局顺序。
    scheduler.add_job(
        _fire_sync_stocks_cn,
        CronTrigger(hour=18, minute=2, timezone=TZ),
        id="cron_sync_stocks_cn",
        name="sync_stocks_cn @ 18:02 daily",
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        _fire_evening_ingestion,
        CronTrigger(hour=18, minute=30, timezone=TZ),
        id="cron_evening_ingestion",
        name="evening_ingestion @ 18:30 daily (handler checks trade_cal_cn)",
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        _fire_screener_runner,
        CronTrigger(hour=19, minute=0, timezone=TZ),
        id="cron_screener_runner",
        name="screener_runner @ 19:00 daily (handler checks trade_cal_cn)",
        misfire_grace_time=3600,
    )

    return scheduler
