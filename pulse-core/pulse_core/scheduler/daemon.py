"""Blocking APScheduler daemon for pulse-core evening automation.

按 docs/architecture.md §7.3 约定常驻运行，不开 HTTP；
负责注册并触发傍晚数据同步任务。

用法:
    uv run python -m pulse_core.scheduler.daemon
"""

import signal
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from pulse_core.lib.logger import logger as _logger  # 触发 loguru 配置初始化

from .jobs import (
    run_evening_ingestion,
    run_screener_placeholder,
    sync_stocks_cn_job,
    sync_trade_cal_cn_job,
)

_ = _logger  # 仅为触发 lib.logger 副作用初始化

_SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

# 所有 job 共用：同一实例只跑一份、错过合并补一次、补跑宽限 1 小时
_MAX_INSTANCES = 1
_COALESCE = True
_MISFIRE_GRACE = 3600


def _register_jobs(scheduler: BlockingScheduler) -> None:
    """Register all fixed cron jobs (times hardcoded for the minimal version)."""
    scheduler.add_job(
        sync_trade_cal_cn_job,
        trigger=CronTrigger(day=1, hour=18, minute=0, timezone=_SHANGHAI_TZ),
        id="trade_cal_cn_monthly",
        max_instances=_MAX_INSTANCES,
        coalesce=_COALESCE,
        misfire_grace_time=_MISFIRE_GRACE,
    )
    scheduler.add_job(
        sync_stocks_cn_job,
        trigger=CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=_SHANGHAI_TZ),
        id="stocks_cn_weekly",
        max_instances=_MAX_INSTANCES,
        coalesce=_COALESCE,
        misfire_grace_time=_MISFIRE_GRACE,
    )
    scheduler.add_job(
        run_evening_ingestion,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=30, timezone=_SHANGHAI_TZ),
        id="evening_ingestion",
        max_instances=_MAX_INSTANCES,
        coalesce=_COALESCE,
        misfire_grace_time=_MISFIRE_GRACE,
    )
    scheduler.add_job(
        run_screener_placeholder,
        trigger=CronTrigger(day_of_week="mon-fri", hour=19, minute=0, timezone=_SHANGHAI_TZ),
        id="screener_placeholder",
        max_instances=_MAX_INSTANCES,
        coalesce=_COALESCE,
        misfire_grace_time=_MISFIRE_GRACE,
    )


def _log_registered_jobs(scheduler: BlockingScheduler) -> None:
    """Log registered job ids and triggers (called before scheduler.start)."""
    jobs = scheduler.get_jobs()
    logger.info(f"Registered {len(jobs)} jobs:")
    for job in jobs:
        logger.info(f"  {job.id} -> trigger={job.trigger}")


def _install_sigint_handler(scheduler: BlockingScheduler) -> None:
    """Install Ctrl+C handler for graceful shutdown (SIGINT only; Windows-compatible)."""

    def _handle(_signum: int, _frame: object | None) -> None:
        logger.info("Shutting down scheduler...")
        if scheduler.running:
            scheduler.shutdown(wait=True)

    signal.signal(signal.SIGINT, _handle)


def main() -> None:
    """Initialize and start the blocking scheduler daemon."""
    logger.info("Initializing scheduler...")
    scheduler = BlockingScheduler(timezone=_SHANGHAI_TZ)
    _register_jobs(scheduler)
    _install_sigint_handler(scheduler)
    _log_registered_jobs(scheduler)
    logger.info("Scheduler started, press Ctrl+C to exit")
    scheduler.start()


if __name__ == "__main__":
    main()
