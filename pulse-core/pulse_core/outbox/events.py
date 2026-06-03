"""notifications_outbox.event_type 取值常量。

新增 event_type 时同步更新 docs/architecture.md §5.4 的 payload schema 示例,
并在 pulse-api/src/notifier/briefing.ts 添加聚合处理逻辑。
"""

from __future__ import annotations

from typing import Final

EVENT_SCREENER_PICKS: Final = "screener_picks"
EVENT_JOB_FAILED:     Final = "job_failed"
EVENT_NOTIFIER_FAILED: Final = "notifier_failed"
