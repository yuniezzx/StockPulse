"""通知出箱（notifications_outbox）写入器。

pulse-core 是该表唯一写入者。pulse-api 是唯一读取者（扫描发送）。

API 设计取舍：
- 不暴露通用 INSERT；按事件类型提供专用函数（enqueue_screener_picks 等）。
  这样 payload 结构与 event_type 强绑定，上游误用直接编译期挡掉。
- 所有函数接收 conn: asyncpg.Connection,要求调用方在事务内调用 ——
  红线 ⑤ "选股 + 虚拟仓 + outbox 同事务原子写入"。
"""

from __future__ import annotations

from pulse_core.outbox.events import (
    EVENT_JOB_FAILED,
    EVENT_NOTIFIER_FAILED,
    EVENT_SCREENER_PICKS,
)
from pulse_core.outbox.writer import enqueue_screener_picks

__all__ = [
    "EVENT_JOB_FAILED",
    "EVENT_NOTIFIER_FAILED",
    "EVENT_SCREENER_PICKS",
    "enqueue_screener_picks",
]
