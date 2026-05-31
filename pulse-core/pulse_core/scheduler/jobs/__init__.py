"""按领域分组的 job handler 包。

每个 `{domain}.py` 文件聚合该领域的所有 handler；handler 在 daemon.py 集中注册。
Handler 合同（详见 scheduler/registry.py）：
- 签名：`async def(run: JobRun) -> JobResult`
- 未捕获异常由 worker 兜底为 status='failed'
- 可恢复的子任务部分失败用 `JobResult(status='partial', details={...})`
"""
