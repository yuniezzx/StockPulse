"""pulse-core 调度守护进程：单进程入口，同时跑 scheduler 和 worker。

启动命令：
    uv run python -m pulse_core.scheduler.daemon

生命周期：
    初始化 logger/pool → 获取 PG advisory lock → 注册 handler
    → 回收上次崩溃残留的 running 行 → 启动 AsyncIOScheduler → 进入 worker 主循环
    → 收到 SIGTERM/SIGINT：停 scheduler、置 stop_event、等 worker
       跑完当前 handler、释放 lock、关 pool、退出。

单实例保证（PG advisory lock）：
    在 _DAEMON_ADVISORY_LOCK_KEY 上持一个 session 级 advisory lock，整个 daemon
    生命周期都不释放。如果已有 daemon 在跑，第二个进程拿不到锁、立即退出。
    session 结束时（崩溃/网络中断/正常关闭）PG 自动释放锁，无需手动清理。

启动时回收残留 running 行：
    上次 daemon 崩溃时留下的 status='running' 行，会被改为 'failed' 并写入
    error_message='daemon restarted...'。该步骤在拿到 advisory lock **之后**
    执行，避免与另一个仍在跑的 daemon 的进行中 handler 撞车。

优雅关闭：
    worker 等当前 handler 自然跑完，不强杀任何 in-flight run。部署时务必给足
    停机宽限期（docker: stop_grace_period: 600s；systemd: TimeoutStopSec=600）。
"""

import asyncio
import signal
import sys
from typing import Final

import asyncpg
from loguru import logger

from pulse_core.lib.db import acquire, close_pool, get_pool
from pulse_core.scheduler.cron import build_scheduler
from pulse_core.scheduler.jobs.ingestion import (
    evening_ingestion_handler,
    sync_stocks_cn_handler,
    sync_trade_cal_cn_handler,
)
from pulse_core.scheduler.jobs.screener import (
    cleanup_screener_history_handler,
    screener_runner_handler,
)
from pulse_core.scheduler.registry import Registry
from pulse_core.scheduler.worker import run_worker

# 调度 daemon 单实例用的 PG advisory lock key。
# 取 "pulsedae"（pulse-core daemon）的 ASCII 字节，避免与共享数据库里其他
# 项目的 advisory lock 撞键。
_DAEMON_ADVISORY_LOCK_KEY: Final[int] = 0x70756C7365646165

_EXIT_OK: Final[int] = 0
_EXIT_LOCK_HELD: Final[int] = 1

_REAP_STALE_RUNNING_SQL = """
UPDATE job_runs
SET status = 'failed',
    finished_at = NOW(),
    error_message = 'daemon restarted while run was in progress; marked stale'
WHERE status = 'running'
"""


def _register_all_handlers(registry: Registry) -> None:
    registry.register("sync_trade_cal_cn", sync_trade_cal_cn_handler)
    registry.register("sync_stocks_cn", sync_stocks_cn_handler)
    registry.register("evening_ingestion", evening_ingestion_handler)
    registry.register("screener_runner", screener_runner_handler)
    registry.register("cleanup_screener_history", cleanup_screener_history_handler)
    logger.info(f"registered {len(registry)} job handlers")


async def _try_acquire_daemon_lock() -> asyncpg.Connection | None:
    pool = await get_pool()
    # 直接从 pool 拿一个 connection，**不**走 context manager：
    # advisory lock 绑在这个 session 上，必须等关机时再把连接还给 pool，
    # 否则连接归还瞬间锁就丢了。
    conn: asyncpg.Connection = await pool.acquire()
    try:
        got = await conn.fetchval("SELECT pg_try_advisory_lock($1)", _DAEMON_ADVISORY_LOCK_KEY)
    except Exception:
        await pool.release(conn)
        raise
    if not got:
        await pool.release(conn)
        return None
    return conn


async def _release_daemon_lock(conn: asyncpg.Connection) -> None:
    pool = await get_pool()
    try:
        await conn.execute("SELECT pg_advisory_unlock($1)", _DAEMON_ADVISORY_LOCK_KEY)
    except Exception:
        # 兜底：即便显式 unlock 失败，归还连接关掉 session 后 PG 也会自动释放锁。
        logger.exception("failed to release daemon advisory lock (will drop on session close)")
    finally:
        await pool.release(conn)


async def _reap_stale_running() -> None:
    async with acquire() as conn:
        result = await conn.execute(_REAP_STALE_RUNNING_SQL)
    reaped = int(result.rsplit(" ", 1)[-1]) if result.startswith("UPDATE") else 0
    if reaped:
        logger.warning(f"reaped {reaped} stale running job_run(s) from previous daemon")
    else:
        logger.info("no stale running job_runs to reap")


def _install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    def _on_signal(sig: signal.Signals) -> None:
        logger.info(f"received {sig.name}, initiating graceful shutdown")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _on_signal, sig)


async def _main() -> int:
    logger.info("pulse-core scheduler daemon starting")

    await get_pool()

    lock_conn = await _try_acquire_daemon_lock()
    if lock_conn is None:
        logger.error(
            f"another scheduler daemon is already running "
            f"(advisory lock {_DAEMON_ADVISORY_LOCK_KEY:#x} held); exiting"
        )
        await close_pool()
        return _EXIT_LOCK_HELD
    logger.info(f"acquired daemon advisory lock {_DAEMON_ADVISORY_LOCK_KEY:#x}")

    try:
        registry = Registry()
        _register_all_handlers(registry)
        await _reap_stale_running()

        stop_event = asyncio.Event()
        _install_signal_handlers(stop_event)

        scheduler = build_scheduler()
        scheduler.start()
        logger.info(f"AsyncIOScheduler started with {len(scheduler.get_jobs())} cron job(s)")

        try:
            await run_worker(stop_event, registry)
        finally:
            logger.info("shutting down scheduler")
            scheduler.shutdown(wait=False)
    finally:
        await _release_daemon_lock(lock_conn)
        await close_pool()
        logger.info("pulse-core scheduler daemon stopped")
    return _EXIT_OK


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
