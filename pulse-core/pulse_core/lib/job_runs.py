"""Data access layer for the `job_runs` table.

Used by both the scheduler (enqueue pending rows) and the worker
(fetch-and-lock, mark running/finished). All SQL lives here so the two
roles never drift apart.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import asyncpg

from pulse_core.lib.db import acquire

JobStatus = Literal["pending", "running", "success", "failed", "partial", "skipped"]
TriggerSource = Literal["cron", "manual", "dependency"]

STATUS_PENDING: JobStatus = "pending"
STATUS_RUNNING: JobStatus = "running"
STATUS_SUCCESS: JobStatus = "success"
STATUS_FAILED: JobStatus = "failed"
STATUS_PARTIAL: JobStatus = "partial"
STATUS_SKIPPED: JobStatus = "skipped"

TRIGGER_CRON: TriggerSource = "cron"
TRIGGER_MANUAL: TriggerSource = "manual"
TRIGGER_DEPENDENCY: TriggerSource = "dependency"


@dataclass(slots=True, frozen=True)
class JobRun:
    id: int
    job_name: str
    trigger_source: TriggerSource
    scheduled_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    status: JobStatus
    rows_affected: int | None
    error_message: str | None
    details: dict[str, Any] | None
    created_at: datetime


_INSERT_PENDING_SQL = """
INSERT INTO job_runs (job_name, trigger_source, scheduled_at, status)
VALUES ($1, $2, $3, 'pending')
RETURNING id
"""

_INSERT_PENDING_CRON_DEDUP_SQL = """
INSERT INTO job_runs (job_name, trigger_source, scheduled_at, status)
VALUES ($1, 'cron', $2, 'pending')
ON CONFLICT (job_name, scheduled_at) WHERE trigger_source = 'cron'
DO NOTHING
RETURNING id
"""

_FETCH_AND_LOCK_PENDING_SQL = """
SELECT id, job_name, trigger_source, scheduled_at, started_at, finished_at,
       status, rows_affected, error_message, details, created_at
FROM job_runs
WHERE status = 'pending'
ORDER BY scheduled_at
FOR UPDATE SKIP LOCKED
LIMIT 1
"""

_MARK_RUNNING_SQL = """
UPDATE job_runs
SET status = 'running', started_at = NOW()
WHERE id = $1 AND status = 'pending'
"""

_MARK_FINISHED_SQL = """
UPDATE job_runs
SET status = $2,
    finished_at = NOW(),
    rows_affected = $3,
    error_message = $4,
    details = $5
WHERE id = $1 AND status = 'running'
"""

_FETCH_BY_ID_SQL = """
SELECT id, job_name, trigger_source, scheduled_at, started_at, finished_at,
       status, rows_affected, error_message, details, created_at
FROM job_runs
WHERE id = $1
"""

_FETCH_LATEST_BY_NAME_SQL = """
SELECT id, job_name, trigger_source, scheduled_at, started_at, finished_at,
       status, rows_affected, error_message, details, created_at
FROM job_runs
WHERE job_name = $1
ORDER BY started_at DESC NULLS LAST, id DESC
LIMIT 1
"""


def _record_to_job_run(record: asyncpg.Record) -> JobRun:
    return JobRun(
        id=record["id"],
        job_name=record["job_name"],
        trigger_source=record["trigger_source"],
        scheduled_at=record["scheduled_at"],
        started_at=record["started_at"],
        finished_at=record["finished_at"],
        status=record["status"],
        rows_affected=record["rows_affected"],
        error_message=record["error_message"],
        details=record["details"],
        created_at=record["created_at"],
    )


async def enqueue(
    job_name: str,
    trigger_source: TriggerSource,
    scheduled_at: datetime,
    *,
    conn: asyncpg.Connection | None = None,
) -> int:
    """Insert a pending job_run; return the new id."""
    if conn is not None:
        return await conn.fetchval(_INSERT_PENDING_SQL, job_name, trigger_source, scheduled_at)
    async with acquire() as c:
        return await c.fetchval(_INSERT_PENDING_SQL, job_name, trigger_source, scheduled_at)


async def enqueue_cron(
    job_name: str,
    scheduled_at: datetime,
    *,
    conn: asyncpg.Connection | None = None,
) -> int | None:
    """Insert a pending cron job_run; return new id or None if already enqueued.

    Used by APScheduler-triggered enqueues. Idempotent against misfire / restart
    via partial unique index on (job_name, scheduled_at) WHERE trigger_source='cron'.
    """
    if conn is not None:
        return await conn.fetchval(_INSERT_PENDING_CRON_DEDUP_SQL, job_name, scheduled_at)
    async with acquire() as c:
        return await c.fetchval(_INSERT_PENDING_CRON_DEDUP_SQL, job_name, scheduled_at)


async def fetch_and_lock_pending(conn: asyncpg.Connection) -> JobRun | None:
    """Fetch one pending run with row-level lock; caller must hold a transaction."""
    row = await conn.fetchrow(_FETCH_AND_LOCK_PENDING_SQL)
    return _record_to_job_run(row) if row else None


def _parse_rowcount(command_tag: str) -> int:
    """Extract the affected-row count from an asyncpg command tag like 'UPDATE 3'."""
    _, _, n = command_tag.rpartition(" ")
    try:
        return int(n)
    except ValueError:
        return 0


async def mark_running(
    run_id: int,
    *,
    conn: asyncpg.Connection | None = None,
) -> bool:
    """Transition pending -> running; return True if the row was updated."""
    if conn is not None:
        result = await conn.execute(_MARK_RUNNING_SQL, run_id)
    else:
        async with acquire() as c:
            result = await c.execute(_MARK_RUNNING_SQL, run_id)
    return _parse_rowcount(result) == 1


async def mark_finished(
    run_id: int,
    status: JobStatus,
    *,
    rows_affected: int | None = None,
    error_message: str | None = None,
    details: dict[str, Any] | None = None,
    conn: asyncpg.Connection | None = None,
) -> None:
    """Transition running -> success | failed | partial | skipped."""
    if conn is not None:
        await conn.execute(
            _MARK_FINISHED_SQL, run_id, status, rows_affected, error_message, details
        )
        return
    async with acquire() as c:
        await c.execute(_MARK_FINISHED_SQL, run_id, status, rows_affected, error_message, details)


async def fetch_by_id(
    run_id: int,
    *,
    conn: asyncpg.Connection | None = None,
) -> JobRun | None:
    """Fetch a single job_run by id."""
    if conn is not None:
        row = await conn.fetchrow(_FETCH_BY_ID_SQL, run_id)
    else:
        async with acquire() as c:
            row = await c.fetchrow(_FETCH_BY_ID_SQL, run_id)
    return _record_to_job_run(row) if row else None


async def fetch_latest_by_name(
    job_name: str,
    *,
    conn: asyncpg.Connection | None = None,
) -> JobRun | None:
    """Fetch the most recent run for a given job_name."""
    if conn is not None:
        row = await conn.fetchrow(_FETCH_LATEST_BY_NAME_SQL, job_name)
    else:
        async with acquire() as c:
            row = await c.fetchrow(_FETCH_LATEST_BY_NAME_SQL, job_name)
    return _record_to_job_run(row) if row else None
