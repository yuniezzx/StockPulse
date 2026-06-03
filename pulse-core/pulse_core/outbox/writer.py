"""按事件类型提供专用 INSERT 函数。

所有函数都要求调用方持有事务,目的是与上游业务写入（picks / virtual_positions）
同事务原子提交（红线 ⑤）。函数本身不开事务,违反者得到 asyncpg 错误。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Final
from zoneinfo import ZoneInfo

import asyncpg

from pulse_core.outbox.events import EVENT_SCREENER_PICKS

_TZ: Final = ZoneInfo("Asia/Shanghai")
_DEFAULT_USER_ID: Final = 1
_BRIEFING_HOUR: Final = 7


@dataclass(frozen=True, slots=True)
class PickPayloadItem:
    """screener_picks 事件 payload 中单条 pick 的最小字段集。

    snake_case 内部键(JSONB 内部规约);pulse-api 出口转 camelCase。
    """

    ts_code:     str
    strategy:    str
    final_score: float
    rank:        int


@dataclass(frozen=True, slots=True)
class TrackPayload:
    track: str
    picks: list[PickPayloadItem]


_INSERT_SQL = """
INSERT INTO notifications_outbox
    (user_id, event_type, payload, scheduled_at)
VALUES
    ($1, $2, $3, $4)
RETURNING id
"""


async def enqueue_screener_picks(
    conn: asyncpg.Connection,
    *,
    trade_date: date,
    run_id: int,
    tracks: list[TrackPayload],
    user_id: int = _DEFAULT_USER_ID,
) -> int:
    """把当日选股结果写入 outbox,scheduled_at = 次日 07:00（早报节奏）。

    必须在调用方事务内调用（与 daily_picks INSERT 同事务,红线 ⑤）。

    Returns:
        新插入行的 id。
    """
    payload: dict[str, Any] = {
        "trade_date": trade_date.isoformat(),
        "run_id":     run_id,
        "tracks": [
            {
                "track": t.track,
                "picks": [
                    {
                        "ts_code":     p.ts_code,
                        "strategy":    p.strategy,
                        "final_score": p.final_score,
                        "rank":        p.rank,
                    }
                    for p in t.picks
                ],
            }
            for t in tracks
        ],
    }
    scheduled_at = _next_briefing_time(trade_date)
    row = await conn.fetchrow(
        _INSERT_SQL,
        user_id,
        EVENT_SCREENER_PICKS,
        payload,
        scheduled_at,
    )
    assert row is not None
    return int(row["id"])


def _next_briefing_time(trade_date: date) -> datetime:
    """trade_date 的次日 07:00 Asia/Shanghai。

    注意:这里"次日"是日历日,周末同样 07:00 触发,
    pulse-api 那边再决定要不要发(避免周末发空早报)。
    """
    next_day = trade_date + timedelta(days=1)
    return datetime.combine(next_day, time(_BRIEFING_HOUR, 0), tzinfo=_TZ)
