# StockPulse

> A 股短中线**个人**选股决策系统。
> 每天傍晚同步数据 → 多策略漏斗选股 → 早晨推送早报 → 追踪持仓 → 校验策略 → 调整权重。
>
> **目标：分析、选股、买卖、追踪、校验、调权。不是回测。**

---

## 文档导航

| 文档 | 内容 |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | **架构决策**：功能版图、三服务边界、数据流、关键机制、目录结构、技术选型 |
| [`docs/naming-conventions.md`](docs/naming-conventions.md) | **命名规则**：DB / Python / TS / 文件名 / 字段对齐 |
| [`AGENTS.md`](AGENTS.md) | **AI 工作守则**：目录速查、新增 checklist、运行命令、红线 |

**冲突解决顺序**（弱 → 强）：
```
README < AGENTS < architecture < naming-conventions < 用户当次明确指示
```

---

## 三服务

```
pulse-core/   Python · uv       · 计算引擎
pulse-api/    TypeScript · pnpm · API 网关 + 通知发送
pulse-web/    TypeScript · pnpm · 前端展示
```

详细职责 → [`docs/architecture.md`](docs/architecture.md) §3。

---

## 6 大功能

```
              ┌──────────────────────────┐
              ▼                          │
          ② 选股 ─→ ④ 持仓 ─→ ⑤ 校验 ─→ ⑥ 权重
              ▲                          │
              └──────────────────────────┘

          ① 股票分析（横向能力）
          ③ 风控（卖出信号）
```

详细 → [`docs/architecture.md`](docs/architecture.md) §2。

---

## 快速跑起来

> **当前状态**：项目正在重构（分支 `refactor/v2-rebuild`），目录骨架未建立。
> 老代码在 [`bak/`](bak/) 下保留。

### 环境要求

- Node.js 20+ / pnpm 9+
- Python 3.12+ / uv
- PostgreSQL 16+
- Tushare token

### 启动（重构完成后）

```bash
# DB
cd pulse-api && pnpm migrate

# 数据同步（傍晚 18:30 cron）
cd pulse-core
uv run python -m pulse_core.ingestion.stocks_cn
uv run python -m pulse_core.ingestion.daily_cn

# 选股（傍晚 18:35 cron）
uv run python -m pulse_core.screener.runner --date 2026-05-21

# 启动 API + Web
cd pulse-api && pnpm dev
cd pulse-web && pnpm dev
```

完整命令 → [`AGENTS.md`](AGENTS.md) §7。

---

## 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 计算 | Python + pandas-ta | 数据生态强 |
| API | TypeScript + Fastify | 与前端共享类型 |
| 前端 | React + Vite + shadcn/ui | 现代、轻量 |
| DB | PostgreSQL | 单一存储（不引 Redis） |
| 调度 | OS cron | 简单稳定 |
| 通知 | 企业微信群机器人 + 邮件 + Telegram | 多通道 |

不引入：Redis / Airflow / Prefect / 消息队列 — 单人项目过度工程。
详细理由 → [`docs/architecture.md`](docs/architecture.md) §7。

---

## 版本

- **v2.0** (`refactor/v2-rebuild`) — 当前。三服务重命名 + 6 功能版图 + outbox 通知 + 半自动权重
- **v1.x** — 已归档到 [`bak/`](bak/)

---

## License

私人项目，未开源。
