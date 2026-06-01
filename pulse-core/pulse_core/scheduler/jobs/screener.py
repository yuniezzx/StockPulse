"""选股 (screener) job handler。

handler 合同：
  async def screener_runner_handler(run: JobRun) -> JobResult

调度时刻见 docs/scheduling.md §5（19:00 daily，紧跟 18:30 evening_ingestion）。
非交易日跳过整个漏斗，避免空跑 + 在 job_runs 留 partial 噪声。

状态映射（screener.RunResult.status → JobResult.status）：
  success → STATUS_SUCCESS
  partial → STATUS_PARTIAL（至少一个 track 失败、至少一个成功）
  failed  → STATUS_FAILED（Stage 0/1 失败 或 全部 track 失败）

总行数 rows_affected = 各 track success.inserted 之和。
details 直接复用 RunResult.to_details()，含每个 track 的 status / inserted / error。
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger

from pulse_core.lib.db import acquire
from pulse_core.lib.job_runs import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
    JobRun,
)
from pulse_core.scheduler.registry import JobResult
from pulse_core.screener.runner import run_screener

# 与 ingestion.py 保持一致：上交所日历即沪深两市权威。
_CALENDAR_EXCHANGE = "SSE"

_IS_TRADING_DAY_SQL = """
SELECT is_open
FROM trade_cal_cn
WHERE exchange = $1 AND cal_date = $2
"""


async def _is_trading_day(date_: datetime) -> bool | None:
    """查 trade_cal_cn 判断给定日期是否交易日。

    返回值同 ingestion._is_trading_day:
      True  → 交易日
      False → 非交易日
      None  → 该日历日未同步（保守继续 + 告警）
    """
    async with acquire() as conn:
        is_open = await conn.fetchval(_IS_TRADING_DAY_SQL, _CALENDAR_EXCHANGE, date_.date())
    if is_open is None:
        return None
    return is_open == 1


async def screener_runner_handler(run: JobRun) -> JobResult:
    """跑当日选股漏斗（全部 tracks）。

    非交易日（周末 / 节假日 / 调休）跳过，返回 status='skipped'。
    日历未覆盖该日时**保守继续执行**，由 partial/failed 暴露日历该补的运维问题。
    """
    trade_date = run.scheduled_at.date()

    trading = await _is_trading_day(run.scheduled_at)
    if trading is False:
        logger.info(f"[run_id={run.id}] {trade_date} 非交易日，跳过 screener_runner")
        return JobResult(
            status=STATUS_SKIPPED,
            details={"reason": "non_trading_day", "date": trade_date.isoformat()},
        )
    if trading is None:
        logger.warning(
            f"[run_id={run.id}] {trade_date} 不在 trade_cal_cn 覆盖范围内，"
            "继续执行 screener（请尽快同步交易日历）"
        )

    logger.info(f"[run_id={run.id}] starting screener_runner for trade_date={trade_date}")
    # run_screener 内部已经做了 per-track 异常隔离 + Stage 0/1 失败上抛。
    # 这里不再 try/except 业务异常：worker 会兜底为 failed。
    result = await run_screener(trade_date)

    details = result.to_details()
    rows = result.total_rows

    if result.status == "success":
        logger.info(
            f"[run_id={run.id}] screener_runner OK "
            f"(trade_date={trade_date} rows={rows} tracks={len(result.track_results)})"
        )
        return JobResult(status=STATUS_SUCCESS, rows_affected=rows, details=details)

    if result.status == "partial":
        failed_tracks = [tr.track for tr in result.track_results if tr.status == "failed"]
        logger.warning(
            f"[run_id={run.id}] screener_runner partial "
            f"(trade_date={trade_date} rows={rows} failed_tracks={failed_tracks})"
        )
        return JobResult(
            status=STATUS_PARTIAL,
            rows_affected=rows,
            details=details,
            error_message=f"track(s) failed: {failed_tracks}",
        )

    # failed：可能是 Stage 0/1 整体失败，也可能是全部 track 都挂
    failed_tracks = [tr.track for tr in result.track_results if tr.status == "failed"]
    logger.error(
        f"[run_id={run.id}] screener_runner FAILED "
        f"(trade_date={trade_date} failed_tracks={failed_tracks})"
    )
    return JobResult(
        status=STATUS_FAILED,
        rows_affected=rows,
        details=details,
        error_message=(
            f"all tracks failed: {failed_tracks}"
            if failed_tracks
            else "screener pipeline failed before per-track stage"
        ),
    )
