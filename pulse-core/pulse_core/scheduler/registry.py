"""Job 注册表：把 job_name 映射到 worker 要调用的 handler 函数。

注册表在 daemon 启动时**显式构造**并传给 worker；**故意不做模块级全局 registry**：
测试、smoke 脚本、生产 daemon 各自持有自己的 Registry 实例，不会跨边界泄漏状态。

Handler 合同：
  - 签名：`async def(run: JobRun) -> JobResult`
  - 未捕获异常由 worker 兜底为 status='failed'
  - 可预见的子任务部分失败用 `JobResult(status='partial')`
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pulse_core.lib.job_runs import JobRun, JobStatus


@dataclass(slots=True, frozen=True)
class JobResult:
    status: JobStatus
    rows_affected: int | None = None
    details: dict[str, Any] | None = None
    error_message: str | None = None


JobHandler = Callable[[JobRun], Awaitable[JobResult]]


class Registry:
    """可变的 name → handler 表。非线程安全；每个 daemon 持有一份。"""

    __slots__ = ("_handlers",)

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_name: str, handler: JobHandler) -> None:
        if job_name in self._handlers:
            raise ValueError(f"job already registered: {job_name}")
        self._handlers[job_name] = handler

    def get(self, job_name: str) -> JobHandler | None:
        return self._handlers.get(job_name)

    def all_names(self) -> list[str]:
        return sorted(self._handlers.keys())

    def __len__(self) -> int:
        return len(self._handlers)
