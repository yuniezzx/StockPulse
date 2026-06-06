# AGENTS.md — StockPulse AI 工作守则

> **精简版**。架构 → [`docs/architecture.md`](docs/architecture.md) ｜ DB → [`docs/database.md`](docs/database.md) ｜ 调度 → [`docs/scheduling.md`](docs/scheduling.md) ｜ 指标 → [`docs/indicators.md`](docs/indicators.md) ｜ 命名 → [`docs/naming-conventions.md`](docs/naming-conventions.md) ｜ 选股 → [`docs/screener.md`](docs/screener.md)
> **冲突解决顺序**：README < AGENTS < architecture < screener < database < scheduling < indicators < naming-conventions < 用户当次明确指示

---

## 0. 一句话

A 股短中线**个人**选股系统：Tushare → 多策略漏斗 → 早报推送 → 持仓追踪 → 策略校验 → 权重调整。
**目标：分析、选股、买卖、追踪、校验、调权。**

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

## 2. 服务边界与指导原则

```
① pulse-core 负责写圈 1/2/3 自动数据；pulse-api 负责写圈 4 用户数据
② pulse-api 建议不做重业务计算；pulse-web 建议零业务计算
③ pulse-core 不开 HTTP 给 pulse-web（前端只通过 pulse-api）
④ 建议用户主动触发的计算优先提前算好走 DB（当前不默认引入 Redis）
⑤ 选股 + 虚拟仓 + outbox 建议优先同事务原子写入
⑥ 通知优先采用 outbox 模式：pulse-core 写表，pulse-api 聚合发送
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

### 新数据表（以 `xxx_cn` 为例）
- [ ] `db/migrations/0YY_create_xxx_cn.sql`
- [ ] 表头注释：用途 + 主键意图 + 单位换算
- [ ] `pulse-core/pulse_core/ingestion/xxx_cn.py`（**同名**）
- [ ] `pulse-core/sql/verify_xxx_cn.sql`
- [ ] 若有跨表 JOIN：在 ingestion 的 SELECT 中保持列序、命名一致

### 新指标
- [ ] `pulse-core/pulse_core/indicators/{domain}.py` 实现 `compute_{indicator}(df)`（domain ∈ trend / momentum / volume / moneyflow）
- [ ] `pulse-core/tests/indicators/test_{domain}.py` 增加用例
- [ ] `db/migrations/0NN_create_daily_{domain}_indicators_cn.sql`（首次创建该 domain 表时；后续新增列改 alter）
- [ ] `pulse-core/pulse_core/indicators/runner.py` 注册 `compute_*` 写入对应 `daily_{domain}_indicators_cn`
- [ ] `pulse-web/src/content/indicator-doc/{domain}/{anchor}.mdx` 按 7 节结构写文档（详见 indicators.md §3）
- [ ] `pulse-web/src/lib/indicator-doc-nav.ts` 注册新 `anchor`，与 mdx 文件名一致
- [ ] `pnpm check:anchors` / `pnpm typecheck` 通过

### 新选股策略
- [ ] `pulse-core/pulse_core/screener/strategies/{strategy_key}.py`
- [ ] 类名 `{StrategyKeyPascalCase}Strategy`，`name = "{strategy_key}"`
- [ ] 在 `pulse-core/pulse_core/screener/tracks/{track}.yaml` 注册
- [ ] `pulse-core/tests/test_{strategy_key}.py`
- [ ] `pulse-web/src/lib/strategy-meta.ts` 增加 key 为 `{strategy_key}` 的元数据条目
- [ ] DB 不需改 schema（`daily_picks.strategy` 是字符串列）
- [ ] 验证：`SELECT DISTINCT strategy FROM daily_picks` 应能查到新值

### 新 API 端点
- [ ] `pulse-api/src/domains/{feature}/`：routes / service / repository / schemas
- [ ] Zod schema 字段 camelCase；repository 负责 snake → camel 转换
- [ ] `pulse-web/src/lib/api/{feature}.ts`：导出 `getXxx` / `postXxx` 等函数
- [ ] `pulse-web/src/types/{feature}.ts`：导出对应 TS 类型（**与后端 Zod 推导类型保持字段一致**）
- [ ] `pulse-web/src/hooks/use-{feature}.ts`：封装数据获取
- [ ] `pulse-web/src/pages/{feature}/{view}.tsx`

### 新通知
- [ ] pulse-core 写 `notifications_outbox`（`scheduled_at` = 次日 07:00；运维告警立即 NOW()）
- [ ] `pulse-api/src/notifier/briefing.ts` 增加该事件的聚合规则
- [ ] 新通道实现放在 `pulse-api/src/notifier/channels/{channel}.ts`

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

### 6.5 Review 必查

1. 新增字段是否泄漏 snake_case 到前端
2. 新增策略 key 三层是否一致（strategy_key / 类名 / tracks yaml / strategy-meta.ts）
3. 新增表是否带正确的市场后缀（如 `_cn`）
4. migration 表头注释是否齐全（用途 / 单位）

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

---

## 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.1 | 2026-06-01 | 恢复并消化 holdings 块 B (checklist) + 块 F (Review 必查)；接入 database/scheduling/indicators；修 MDX broken-ref |
