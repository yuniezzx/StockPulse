"""Smoke test for Step 5: worker end-to-end.

Verifies: enqueue -> _run_once -> _claim_one -> _execute -> mark_finished.
Cleans up its own test rows.
"""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from pulse_core.lib.db import acquire, close_pool
from pulse_core.lib.job_runs import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    TRIGGER_MANUAL,
    JobRun,
    enqueue,
    fetch_by_id,
)
from pulse_core.scheduler.registry import JobResult, Registry
from pulse_core.scheduler.worker import _run_once

TZ = ZoneInfo("Asia/Shanghai")


async def ok_handler(run: JobRun) -> JobResult:
    return JobResult(
        status=STATUS_SUCCESS,
        rows_affected=42,
        details={"note": "ok"},
    )


async def raising_handler(run: JobRun) -> JobResult:
    raise RuntimeError("boom")


async def partial_handler(run: JobRun) -> JobResult:
    return JobResult(
        status=STATUS_PARTIAL,
        rows_affected=10,
        details={"success": {"a": 5, "b": 5}, "failed": {"c": "x"}},
        error_message="1 sub-task failed: ['c']",
    )


async def assert_final(run_id: int, *, status: str, rows_affected: int | None) -> None:
    final = await fetch_by_id(run_id)
    assert final is not None, f"run {run_id} missing"
    assert final.status == status, f"expected status={status}, got {final.status}"
    assert final.rows_affected == rows_affected, (
        f"expected rows={rows_affected}, got {final.rows_affected}"
    )
    assert final.started_at is not None
    assert final.finished_at is not None
    print(
        f"  run_id={run_id} status={final.status} rows={final.rows_affected} "
        f"details={final.details}"
    )


async def cleanup(ids: list[int]) -> None:
    if not ids:
        return
    async with acquire() as conn:
        await conn.execute("DELETE FROM job_runs WHERE id = ANY($1::bigint[])", ids)


async def main() -> None:
    registry = Registry()
    registry.register("smoke_ok", ok_handler)
    registry.register("smoke_raise", raising_handler)
    registry.register("smoke_partial", partial_handler)

    ids: list[int] = []
    now = datetime.now(tz=TZ)

    print(">>> case 1: success")
    id1 = await enqueue("smoke_ok", TRIGGER_MANUAL, now)
    ids.append(id1)
    assert await _run_once(registry) is True
    await assert_final(id1, status=STATUS_SUCCESS, rows_affected=42)

    print(">>> case 2: exception -> failed")
    id2 = await enqueue("smoke_raise", TRIGGER_MANUAL, now)
    ids.append(id2)
    assert await _run_once(registry) is True
    final2 = await fetch_by_id(id2)
    assert final2.status == STATUS_FAILED
    assert "RuntimeError: boom" in (final2.error_message or "")
    print(
        f"  run_id={id2} status={final2.status} error_message_head="
        f"{(final2.error_message or '')[:60]!r}"
    )

    print(">>> case 3: partial")
    id3 = await enqueue("smoke_partial", TRIGGER_MANUAL, now)
    ids.append(id3)
    assert await _run_once(registry) is True
    await assert_final(id3, status=STATUS_PARTIAL, rows_affected=10)

    print(">>> case 4: unknown job -> failed")
    id4 = await enqueue("smoke_unknown_job_xyz", TRIGGER_MANUAL, now)
    ids.append(id4)
    assert await _run_once(registry) is True
    final4 = await fetch_by_id(id4)
    assert final4.status == STATUS_FAILED
    assert "unknown job" in (final4.error_message or "")
    print(
        f"  run_id={id4} status={final4.status} "
        f"error_message={final4.error_message!r}"
    )

    print(">>> case 5: no pending -> _run_once returns False")
    assert await _run_once(registry) is False
    print("  ok")

    await cleanup(ids)
    await close_pool()
    print(">>> all 5 cases passed")


if __name__ == "__main__":
    asyncio.run(main())
