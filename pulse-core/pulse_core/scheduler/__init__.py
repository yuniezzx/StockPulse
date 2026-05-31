"""调度子系统：cron 触发器 + worker 主循环 + job 注册表。

调度子系统由四个组件构成（详见 AGENTS.md §3）：
- `daemon.py`   常驻进程入口，持有 PG advisory lock 保证单实例
- `cron.py`     APScheduler 配置：到点写 pending 行（不执行业务）
- `worker.py`   轮询 job_runs 表，调用 registry 里的 handler 执行
- `registry.py` job_name → handler 映射；jobs/{domain}.py 是具体实现

通过"写表 + 轮询"解耦定时触发与业务执行，换来可观测性、手动重跑能力、
以及崩溃恢复能力（advisory lock + stale-running reaping）。
"""
