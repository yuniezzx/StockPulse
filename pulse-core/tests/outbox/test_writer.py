"""单元测试 pulse_core.outbox.writer.enqueue_screener_picks。

不连真 DB,用 fake conn 截获 INSERT 调用,断言:
- SQL 落到 notifications_outbox(单条 INSERT)
- payload JSONB 结构与 docs/architecture.md §5.4 一致
- scheduled_at = trade_date 的次日 07:00 Asia/Shanghai
- 返回 fetchrow 给的 id
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from pulse_core.outbox.events import EVENT_SCREENER_PICKS
from pulse_core.outbox.writer import (
    PickPayloadItem,
    TrackPayload,
    enqueue_screener_picks,
)


class _FakeConn:
    def __init__(self, returning_id: int = 42) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self._returning_id = returning_id

    async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any]:
        self.calls.append((sql, args))
        return {"id": self._returning_id}


def _payload(conn: _FakeConn) -> dict[str, Any]:
    sql, args = conn.calls[0]
    assert "notifications_outbox" in sql
    payload = args[2]
    assert isinstance(payload, dict), (
        f"payload 必须是 dict(交给 asyncpg jsonb codec),实际 {type(payload).__name__}"
    )
    return payload


@pytest.mark.asyncio
async def test_enqueue_screener_picks_inserts_one_row():
    conn = _FakeConn(returning_id=99)
    tracks = [
        TrackPayload(
            track="scalp",
            picks=[
                PickPayloadItem(
                    ts_code="600726.SH",
                    strategy="limit_up_replay",
                    final_score=84.72,
                    rank=1,
                ),
            ],
        ),
    ]

    outbox_id = await enqueue_screener_picks(
        conn,  # type: ignore[arg-type]
        trade_date=date(2026, 6, 2),
        run_id=36,
        tracks=tracks,
    )

    assert outbox_id == 99
    assert len(conn.calls) == 1


@pytest.mark.asyncio
async def test_enqueue_screener_picks_payload_shape():
    conn = _FakeConn()
    tracks = [
        TrackPayload(
            track="scalp",
            picks=[
                PickPayloadItem(
                    ts_code="600726.SH", strategy="limit_up_replay",
                    final_score=84.72, rank=1,
                ),
                PickPayloadItem(
                    ts_code="000001.SZ", strategy="limit_up_replay",
                    final_score=70.5, rank=2,
                ),
            ],
        ),
        TrackPayload(track="swing", picks=[]),
    ]

    await enqueue_screener_picks(
        conn,  # type: ignore[arg-type]
        trade_date=date(2026, 6, 2),
        run_id=36,
        tracks=tracks,
    )

    payload = _payload(conn)
    assert payload["trade_date"] == "2026-06-02"
    assert payload["run_id"] == 36
    assert len(payload["tracks"]) == 2

    scalp = payload["tracks"][0]
    assert scalp["track"] == "scalp"
    assert len(scalp["picks"]) == 2
    assert scalp["picks"][0] == {
        "ts_code":     "600726.SH",
        "strategy":    "limit_up_replay",
        "final_score": 84.72,
        "rank":        1,
    }

    assert payload["tracks"][1] == {"track": "swing", "picks": []}


@pytest.mark.asyncio
async def test_enqueue_uses_event_type_and_default_user():
    conn = _FakeConn()
    await enqueue_screener_picks(
        conn,  # type: ignore[arg-type]
        trade_date=date(2026, 6, 2),
        run_id=1,
        tracks=[TrackPayload(track="scalp", picks=[])],
    )
    _, args = conn.calls[0]
    user_id, event_type, _payload_json, _scheduled_at = args
    assert user_id == 1
    assert event_type == EVENT_SCREENER_PICKS


@pytest.mark.asyncio
async def test_enqueue_custom_user_id_propagates():
    conn = _FakeConn()
    await enqueue_screener_picks(
        conn,  # type: ignore[arg-type]
        trade_date=date(2026, 6, 2),
        run_id=1,
        tracks=[TrackPayload(track="scalp", picks=[])],
        user_id=7,
    )
    user_id = conn.calls[0][1][0]
    assert user_id == 7


@pytest.mark.asyncio
async def test_scheduled_at_is_next_day_seven_am_shanghai():
    conn = _FakeConn()
    await enqueue_screener_picks(
        conn,  # type: ignore[arg-type]
        trade_date=date(2026, 6, 2),
        run_id=1,
        tracks=[TrackPayload(track="scalp", picks=[])],
    )
    scheduled_at = conn.calls[0][1][3]
    assert isinstance(scheduled_at, datetime)
    assert scheduled_at == datetime(
        2026, 6, 3, 7, 0, tzinfo=ZoneInfo("Asia/Shanghai"),
    )


@pytest.mark.asyncio
async def test_scheduled_at_handles_month_rollover():
    conn = _FakeConn()
    await enqueue_screener_picks(
        conn,  # type: ignore[arg-type]
        trade_date=date(2026, 6, 30),
        run_id=1,
        tracks=[TrackPayload(track="scalp", picks=[])],
    )
    scheduled_at = conn.calls[0][1][3]
    assert scheduled_at == datetime(
        2026, 7, 1, 7, 0, tzinfo=ZoneInfo("Asia/Shanghai"),
    )
