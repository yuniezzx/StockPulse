# StockPulse 任务调度

> **本文是 StockPulse 调度机制的唯一来源。**
> 总体服务边界见 [`architecture.md`](architecture.md) §3；本文内容源自 §7.2–§7.3。

---

## 1. 设计目标

| 目标 | 说明 |
|---|---|
| 跨平台 | Windows / Linux / macOS 同一套代码跑，无需为每个 OS 维护独立配置 |
| 可观测 | `job_runs` 表持久化每次运行状态，pulse-api 可查历史 |
| 可手动触发 | pulse-api INSERT 一行 `pending`，worker 自动捞起；无需进程间通信 |
| 崩溃恢复 | daemon 重启时 reap `status='running'` → `'failed'`，不留僵尸行 |

---

## 2. 选型理由

任务量少（每日 5–10 个 job），依赖关系简单（串行为主），OS 级调度方案需多平台配置，不可接受。

| 备选 | 否决理由 |
|---|---|
| Airflow / Prefect | 过度工程 |
| OS cron | ❌ 仅 Unix；Windows 需另写 Task Scheduler 配置 |
| Windows Task Scheduler | ❌ 仅 Windows |
| systemd timer | ❌ 仅 Linux |
| Celery beat | 过度工程（需要 broker） |
| **APScheduler** | ✅ 纯 Python、跨平台、cron 语法、单进程常驻 |

---

## 3. 执行模型

### 3.1 方案对比（A vs B）

APScheduler 不直接调用 handler，而是写一行 `job_runs` `status='pending'`，由 worker 异步执行（**方案 B**）。

| 需求 | 方案 A：仅用 APScheduler | 方案 B：scheduler/worker 分离 |
|---|---|---|
| 运行历史可观测 | ❌ 只在日志 | ✅ 查 `job_runs` 表 |
| 手动触发 | ❌ 进程内函数 pulse-api 调不到 | ✅ pulse-api INSERT 一行 pending，worker 自动捞起 |
| 失败通知 | ❌ 异常只能进程内 try/except | ✅ worker 标 failed 时同事务写 outbox |
| 崩溃恢复 | ❌ 需要自建状态机 | ✅ 启动时 reap `status='running'` → `failed` |

### 3.2 运行时结构

`daemon.py` 通过 `asyncio.run()` 同时启动两个协程：

```
AsyncIOScheduler（定时写 job_runs pending）
        ↓  INSERT job_runs(status='pending')
worker（SELECT FOR UPDATE SKIP LOCKED，1s 轮询）
        ↓  调用 registry 中注册的 handler
job_runs(status='done' / 'failed')
```

---

## 4. 落地组件

| 文件 | 职责 |
|---|---|
| `scheduler/daemon.py` | 常驻进程入口；`asyncio.run()` 同时跑 scheduler + worker；收到 SIGTERM/SIGINT 后等当前 handler 自然结束再退出（`stop_grace_period: 600s`）；**不开 HTTP**（架构红线 §3.2 ④） |
| `scheduler/cron.py` | APScheduler 定义；使用 `AsyncIOScheduler`（非 `BlockingScheduler`，与 worker 同 event loop）；触发器只调 `enqueue_cron(job_name, now)`，不执行业务逻辑；幂等：`(job_name, scheduled_at) WHERE trigger_source='cron'` partial unique index 防止 misfire 重复入队 |
| `scheduler/worker.py` | 执行循环；`SELECT ... FOR UPDATE SKIP LOCKED` + 1 秒轮询；并发 = 1（Tushare 限流，串行）；handler 异常兜底为 `status='failed'`，不让 worker 崩溃 |
| `scheduler/registry.py` | job_name → handler 映射注册表 |
| `scheduler/jobs/` | 各领域 job handler（当前：`ingestion.py`） |

**启动命令**（任何平台）：

```bash
uv run python -m pulse_core.scheduler.daemon
```

生产保活：systemd / Windows 服务 / pm2，按部署平台自选。

---

## 5. 当前 cron 表

| job_name | 时刻 | 用途 |
|---|---|---|
| `sync_trade_cal_cn` | 18:00 daily | 同步交易日历（为次日盘前准备） |
| `sync_stocks_cn` | 18:02 daily | 同步股票列表（新股 / 退市，错开 2 分钟避免与 sync_trade_cal_cn 同秒入队） |
| `evening_ingestion` | 18:30 daily | 拉日线 / 复权 / 涨跌停 / 估值 / 资金流 + 计算 4 张派生指标表（6 子任务串行，支持 partial） |
| `screener_runner` | 19:00 daily | 选股漏斗（5 stage：交易日检查 / 数据加载 / Layer 1+2 过滤 / 策略打分 / 双表原子写入；非交易日 skipped；track 部分失败 partial） |
| `cleanup_screener_history` | 04:00 weekly (Sun) | 滚动清理 daily_picks + daily_pick_candidates 超过 365 天的行（单事务双表删除） |

---

## 6. 待办 jobs

以下 job 待对应模块落地后再加：

- `risk_scan` — 风控扫描（待 risk 模块）
- `morning_briefing` — 早报生成（待 outbox 模块）

> 注：pulse-api 一侧的 07:00 早报发送走 Fastify 进程内 cron（fastify-cron），不属于本 daemon 管辖范围。

---

## 7. 代价与取舍

APScheduler 为进程内调度，进程挂掉不会像 OS cron 那样由系统自动续跑。

单人项目场景下可接受——进程挂了早报收不到立刻可知。

---

## 修订记录

| 版本 | 日期 | 说明 |
|---|---|---|
| v1.0 | 2026-06-01 | 从 architecture.md §7.2–§7.3 抽出独立成文 |
