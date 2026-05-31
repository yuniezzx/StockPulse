# AGENTS.md — StockPulse AI 工作守则

> **精简版**。架构 → [`docs/architecture.md`](docs/architecture.md) ｜ 命名 → [`docs/naming-conventions.md`](docs/naming-conventions.md)
> **冲突解决顺序**：本文 < architecture < naming-conventions < 用户当次明确指示

---

## 0. 一句话

A 股短中线**个人**选股系统：Tushare → 多策略漏斗 → 早报推送 → 持仓追踪 → 策略校验 → 权重调整。
**目标：分析、选股、买卖、追踪、校验、调权。不是回测。**

## 0.1 三服务

```
pulse-core/   Python · uv       · 计算引擎（同步 + 选股 + 风控 + 校验 + 写自动数据）
pulse-api/    TypeScript · pnpm · API 网关 + 通知发送 + 用户数据写入
pulse-web/    TypeScript · pnpm · 前端展示（零业务计算）
```

详细职责见 [`docs/architecture.md`](docs/architecture.md) §3。

---

## 1. 命名（必背 3 条）

1. DB / Python / SQL → `snake_case`；TypeScript → `camelCase`；文件名 → `kebab-case`（Python 用 `snake_case`，SQL migration 用 `序号_snake_case`）
2. **Tushare 原字段不重命名**；snake_case **禁止泄漏**到前端类型
3. 跨语言契约关键字段：`ts_code` ↔ `tsCode`、`trade_date` ↔ `tradeDate`、策略 key 三层完全一致

完整规则 → [`docs/naming-conventions.md`](docs/naming-conventions.md)。

---

## 2. 边界铁律（红线）

```
① pulse-core 写圈 1/2/3 自动数据；pulse-api 写圈 4 用户数据
② pulse-api 不做重业务计算；pulse-web 零业务计算
③ pulse-core 不开 HTTP 给 pulse-web（前端只通过 pulse-api）
④ 用户主动触发计算 → 提前算好走 DB（不用 Redis）
⑤ 选股 + 虚拟仓 + outbox 必须同事务原子写入
⑥ 通知用 outbox：pulse-core 写表，pulse-api 在 07:00 聚合发送
```

详细规则 → [`docs/architecture.md`](docs/architecture.md) §3.2 / §4.4。

---

## 3. 目录速查

```
pulse-core/pulse_core/
  lib/           共享：db / config / logger / time / tushare_client
  ingestion/     数据同步（一表一文件，文件名 = 表名）
  indicators/    指标 + 形态（按 domain 切分：trend/momentum/volume/moneyflow + runner.py）
  screener/      选股（filters/ strategies/ tracks/ runner.py）
  tracking/      虚拟仓自动追踪
  risk/          风控（卖出信号）
  evaluation/    策略校验
  weights/       权重建议
  outbox/        通知出箱
  scheduler/     任务编排（daemon + scheduler + worker + job_runs）
                 daemon.py 是常驻进程入口
                 cron.py 到点写 pending 行 / worker.py 轮询执行
                 jobs/{domain}.py 是 handler 实现

pulse-api/src/
  domains/{feature}/  routes.ts + service.ts + repository.ts + schemas.ts
  notifier/           扫 outbox → 发企业微信/邮件
  plugins/            cors / jwt / cron

pulse-web/src/
  pages/{feature}/    路由页面
  components/         ui/ (shadcn) · layout/ · auth/ · {feature}/
  lib/api/            一个 feature 一文件
  hooks/  store/  types/
```

完整树 → [`docs/architecture.md`](docs/architecture.md) §6。

---

## 4. 新增 checklist

### 新数据表
- [ ] `db/migrations/0NN_create_xxx.sql`（表头注释：用途 + 主键 + 单位）
- [ ] `pulse-core/pulse_core/ingestion/xxx.py`（**同名**）
- [ ] `pulse-core/sql/verify_xxx.sql`

### 新指标
- [ ] `pulse-core/pulse_core/indicators/{domain}.py` 实现 `compute_{indicator}(df)`（domain ∈ trend / momentum / volume / moneyflow）
- [ ] `pulse-core/tests/indicators/test_{domain}.py` 增加用例
- [ ] `db/migrations/0NN_create_daily_{domain}_indicators_cn.sql`（首次创建该 domain 表时；后续新增列改 alter）
- [ ] `pulse-core/pulse_core/indicators/runner.py` 注册 `compute_*` 写入对应 `daily_{domain}_indicators_cn`
- [ ] `pulse-web/src/content/indicator-doc/{domain}/{anchor}.mdx` 按 7 节结构写文档（详见 naming-conventions §四点八）
- [ ] `pulse-web/src/lib/indicator-doc-nav.ts` 注册新 `anchor`，与 mdx 文件名一致
- [ ] `pnpm check:anchors` / `pnpm typecheck` 通过

### 新选股策略
- [ ] `pulse-core/pulse_core/screener/strategies/{key}.py`
- [ ] 类 `{Key}Strategy`，`name = "{key}"`
- [ ] 在某个 `tracks/{track}.yaml` 注册
- [ ] `pulse-web/src/lib/strategy-meta.ts` 增加元数据

### 新 API 端点
- [ ] `pulse-api/src/domains/{feature}/`：routes / service / repository / schemas
- [ ] Zod schema 字段 camelCase；repository 做 snake → camel 转换
- [ ] `pulse-web/src/lib/api/{feature}.ts`：`getXxx` / `postXxx`
- [ ] `pulse-web/src/hooks/use-{feature}.ts`
- [ ] `pulse-web/src/pages/{feature}/{view}.tsx`

### 新通知
- [ ] pulse-core 写 `notifications_outbox`（`scheduled_at` = 次日 07:00；运维告警立即 NOW()）
- [ ] pulse-api `notifier/briefing.ts` 决定如何聚合
- [ ] 通道实现在 `pulse-api/src/notifier/channels/`

### 新定时任务
- [ ] handler 实现：`pulse-core/pulse_core/scheduler/jobs/{domain}.py`
- [ ] 签名 `async def {name}_handler(run: JobRun) -> JobResult`
- [ ] handler 内部异常**向上抛**（worker 兜底为 failed）；可恢复的子任务失败用 `JobResult(status='partial', details={...})`
- [ ] `daemon.py` 内 `register("{job_name}", {name}_handler)` 集中注册
- [ ] `cron.py` 添加 `scheduler.add_job(...)` + `_fire_{name}()` 触发器
- [ ] `job_name` 命名 = snake_case，对应明确的领域动作（如 `sync_stocks_cn` / `evening_ingestion`）

---

## 5. 工作流默认要求

- 改前先 grep 类似模式（与现有风格一致 > 发明新风格）
- 改完 TS：`pnpm typecheck` + `pnpm lint` 必须过
- 改完 Python：`uv run pytest tests/test_xxx.py`
- 改完 SQL migration：根目录 `pnpm db:migrate` 跑通 + 写 `verify_xxx.sql`
- 跨语言契约改动（策略 key / 字段重命名）→ **三层同步**改

---

## 6. 红线（禁止）

```ts
// ❌ snake_case 泄漏到前端
interface Item { ts_code: string }              // 应 tsCode

// ❌ 类型加 I / T 前缀
interface IItem {}  type TItem = {}

// ❌ 组件文件 PascalCase
PicksCard.tsx                                    // 应 picks-card.tsx

// ❌ 股票代码乱起名
{ code: string }  { symbol: string }             // 应 tsCode
```

```python
# ❌ 类名不是 snake_case 的 name 字段
class MACDStrategy:
    name = "MACD"                                # 应 "macd"
```

```sql
-- ❌ 跨市场表漏后缀
CREATE TABLE daily (...);                        -- 应 daily_cn

-- ❌ ingestion 文件名 ≠ 表名
ingestion/sync_daily.py                          -- 应 daily_cn.py
```

---

## 7. 运行命令

```bash
# 所有命令在仓库根目录执行（pnpm workspace）

# DB migration
pnpm db:migrate

# 数据同步（手动跑一次，建议首次拉历史数据用）
cd pulse-core
uv run python -m pulse_core.ingestion.stocks_cn
uv run python -m pulse_core.ingestion.daily_cn

# 定时任务常驻进程（接管每日 18:00 / 18:30 自动同步）
uv run python -m pulse_core.scheduler.daemon

# 选股
uv run python -m pulse_core.screener.runner --date 2026-05-21

# 启动
pnpm api:dev
pnpm web:dev

# 校验
pnpm api:typecheck && pnpm api:lint
pnpm web:typecheck && pnpm web:lint
cd pulse-core && uv run pytest
```

---

## 8. Git 约定

- 分支：`{type}/{kebab-case}`（type ∈ feature/fix/chore/docs/refactor/perf/test）
- Commit：`{type}({scope}): {subject}`
  - scope = 顶层目录：`core` / `api` / `web` / `db` / `docs` / `infra`
- 示例：
  - `feat(core): add macd cross strategy`
  - `fix(api): handle empty picks in resonance query`
  - `docs(arch): 重构架构文档 v2`
