# AGENTS.md — StockPulse AI 工作守则

> **写给 AI 助手读的精简规则**。完整版见 [`docs/naming-conventions.md`](docs/naming-conventions.md)。
> **遇到冲突时，本文件 < `docs/naming-conventions.md` < 用户当次明确指示**。

---

## 0. 项目一句话

A 股短中线选股系统：Tushare 同步 → 多策略打分 → Web 展示 + 通知。
**目标：分析、选股、买卖（不是回测）**。

## 0.1 仓库结构

```
api/      Fastify + TS + Postgres（pnpm）
web/      Vite + React 19 + TS + Tailwind + shadcn（pnpm）
engine/   Python 3 + asyncpg + pandas-ta（uv）—— ingestion / screener / compute
db/       migrations/（按序号命名的 SQL）
docs/     naming-conventions.md（命名规范完整版）
```

---

## 1. 命名总原则（背下来）

> **边界 1:1 对齐外部源；内部统一语言习惯；跨边界处显式转换。**

- DB / Python / SQL → **`snake_case`**
- TypeScript（api + web）→ **`camelCase`**
- 文件名 → **`kebab-case`**（Python 用 `snake_case`、SQL migration 用带序号 `snake_case`）
- **Tushare 原字段不重命名**
- **snake_case 不允许泄漏到前端类型**

---

## 2. 跨语言契约（最重要的表）

| 概念 | DB 列 | Python | TypeScript |
|---|---|---|---|
| 股票代码 | `ts_code` | `ts_code` | `tsCode`（**禁止** `code` / `symbol`） |
| 交易日 | `trade_date` | `trade_date` | `tradeDate`（TS 用 `string`，`YYYY-MM-DD`） |
| 策略 key | `strategy` 列值 | `Screener.name` | union literal | snake_case 三层完全一致 |
| 打分 | `score` (float) | `Pick.score` | `score: number`（0–100） |
| 信号详情 | `signals` JSONB | `Pick.signals: dict` | `Record<string, unknown>` |
| 总分 | `total_score` | `total_score` | `totalScore` |
| 共振数 | `strategy_count` | `strategy_count` | `strategyCount` |
| 创建时间 | `created_at` | `created_at` | `createdAt` |

**策略 key 必须三层完全一致**：
| 类 | `name` 属性 = DB 值 = 前端 key |
|---|---|
| `BreakoutScreener` | `"breakout"` |
| `PullbackScreener` | `"pullback"` |
| `MACDCrossScreener` | `"macd_cross"` |
| `LimitUpScreener` | `"limit_up"` |
| `MoneyflowScreener` | `"moneyflow"` |
| `SectorLeaderScreener` | `"sector_leader"` |

---

## 3. 三块代码的命名速查

### 3.1 数据库

- 市场数据表：`{tushare接口名}_cn`（例 `daily_cn`、`adj_factor_cn`）
- 业务表：`snake_case`，**不加** `_cn`（例 `daily_picks`、`users`）
- 列：`snake_case`，保留 Tushare 原字段名
- 时间字段：日期 `_date`、时间戳 `_at`（用 `TIMESTAMPTZ`）
- 布尔：`is_xxx` / `has_xxx`，禁止 `xxx_flag`
- 索引：`idx_{表}_{字段1}_{字段2}`
- Migration：`db/migrations/{3位序号}_{create|alter|drop|seed|backfill}_{对象}.sql`
- 表头**必须**注释：用途 / 主键意图 / 单位换算

### 3.2 Python（engine/）

- 文件：`snake_case.py`
- **ingestion 文件名 = 表名**：`engine/ingestion/daily_cn.py` ↔ `daily_cn` 表
- **screener 文件名 = 策略 key**：`engine/screener/breakout.py` ↔ `name = "breakout"`
- 类：`PascalCase`，缩写保留全大写（`MACDCrossScreener`、`ATR`）
- 函数 / 变量：`snake_case`，私有加 `_` 前缀
- 常量：`UPPER_SNAKE_CASE`（私有 `_UPPER_SNAKE`）
- 复权列：`{原列}_qfq`（例 `close_qfq`）；指标列直接拼数字（`ma20` 不是 `ma_20`）
- 异步：`async with acquire() as conn` + `async with conn.transaction()`
- 日志：`from loguru import logger`，格式 `f"[{name}] {msg}"`

### 3.3 TypeScript（api/ + web/）

**文件名**：
- 普通 ts / tsx：`kebab-case`
- React 组件文件：`kebab-case.tsx`（**不是** PascalCase）
- 页面：`pages/{feature}/{view}.tsx`，目录 = 路由

**标识符**：
- 变量 / 函数：`camelCase`
- 组件：`PascalCase`
- Hook：`useXxx`
- Type / Interface：`PascalCase`，**禁止** `I` / `T` 前缀
- Zod schema：`xxxSchema`；推导类型 `Xxx`
- 常量：`UPPER_SNAKE_CASE`
- 联合字符串字面量（策略等）：`snake_case`，跟 DB 对齐

**API 边界（最重要）**：
- repository 内部用 snake_case row 类型（如 `ResonanceRow`）
- 暴露给 routes / 前端的对象**强制 camelCase**（如 `ResonanceItem`）
- 转换发生在 `api/src/domains/{feature}/repository.ts` 或 `service.ts`

**三层一致命名**：
| 层 | 命名 |
|---|---|
| API 函数 | `getXxx` / `postXxx` / `putXxx` / `deleteXxx` |
| Hook | `useXxx`（去掉动词） |
| 页面 | `XxxPage` |
| 业务组件 | `XxxCard` / `XxxBadge` / `XxxList` / `XxxTable` |

---

## 4. 目录组织（**新文件放对地方**）

### api/src/
```
server.ts
config/                   # 环境变量校验
plugins/                  # Fastify 插件（cors、jwt）
adapters/                 # 外部资源（db pool）
domains/{feature}/        # 业务域
├── routes.ts             # 薄：校验参数 + 调 service
├── service.ts            # 业务逻辑
├── repository.ts         # DB 访问 + snake→camel 转换
└── schemas.ts            # Zod schema + 导出类型
```

### web/src/
```
main.tsx
router/
pages/{feature}/          # 路由页面
components/
├── ui/                   # shadcn 原子组件，禁业务逻辑
├── layout/               # 布局（sidebar / header）
├── auth/                 # 认证守卫
└── {feature}/            # 业务组件
hooks/                    # use-xxx.ts
store/                    # zustand
lib/
├── api/                  # 一个 feature 一文件
├── utils.ts              # cn() 等
└── {feature}-meta.ts     # 业务元数据
types/                    # 跨 feature 共享类型
```

### engine/
```
lib/                      # 共享：config / db / tushare client
ingestion/                # 数据同步（一表一文件，命名 = 表名）
compute/                  # 纯函数指标（indicators / adjust）
screener/                 # 策略实现（一策略一文件，命名 = 策略 key）
└── runner.py             # 编排 + 写库
notify/                   # 通知通道（待建）
server/                   # 未来 FastAPI
tests/                    # test_{被测模块}.py
sql/                      # 验证脚本 verify_xxx.sql
```

---

## 5. 新增 checklist（动手前看一眼）

### 新数据表 `xxx_cn`
- [ ] `db/migrations/0YY_create_xxx_cn.sql`（表头写用途 + 主键意图 + 单位换算）
- [ ] `engine/ingestion/xxx_cn.py`（**同名**）
- [ ] `engine/sql/verify_xxx_cn.sql`
- [ ] `README.md` 数据清单表更新

### 新选股策略
- [ ] `engine/screener/{key}.py`
- [ ] 类 `{KeyPascal}Screener` + `name = "{key}"`
- [ ] 注册到 `engine/screener/runner.py` 的 `SCREENERS`
- [ ] `engine/tests/test_{key}.py`
- [ ] `web/src/lib/strategy-meta.ts` 增加该 key 的元数据（label / description / badgeClass / barClass）

### 新 API 端点
- [ ] `api/src/domains/{feature}/`：routes / service / repository / schemas
- [ ] Zod schema 字段 **camelCase**，repository 做 snake→camel 转换
- [ ] `web/src/lib/api/{feature}.ts`：`getXxx` / `postXxx`
- [ ] `web/src/types/{feature}.ts`：与后端 Zod 推导类型字段一致
- [ ] `web/src/hooks/use-{feature}.ts`
- [ ] `web/src/pages/{feature}/{view}.tsx`

---

## 6. 单位换算（在 ingestion 层做）

| Tushare 字段 | 原单位 | 入库 | 转换 |
|---|---|---|---|
| `vol` (daily) | 手 | 股 | × 100 |
| `amount` (daily) | 千元 | 元 | × 1000 |
| `total_mv` / `circ_mv` (daily_basic) | 万元 | 元 | × 10000 |
| `adj_factor` | — | — | 直接存 |

**入库统一基础单位（元 / 股 / %）**，前端不做单位换算。

---

## 7. 关键全局约定

- `engine/` 是 Python 项目根，import **不带** `engine.` 前缀
- 历史起始日期常量：`HISTORY_START_DATE = date(2023, 1, 1)`
- 增量同步：基于 `trade_cal_cn` 回溯 **3 个交易日**（OFFSET，不是自然日）
- 写库统一：`ON CONFLICT DO UPDATE`（覆盖订正）
- Tushare 调用：`@tushare_retry` + `SLEEP_BETWEEN_CALLS = 0.5`
- 复权：选股相关计算**必须用前复权价**（`close_qfq` 等）；展示价用原始 `close`

---

## 8. Git 约定

- 分支：`{type}/{kebab-case}`，type ∈ `feature` / `fix` / `chore` / `docs` / `refactor` / `perf` / `test`
- Commit（Conventional Commits）：`{type}({scope}): {subject}`
  - scope = 顶层目录：`api` / `web` / `engine` / `db` / `notify` / `infra` / `docs`
  - subject 祈使语气，不加句号，中英文均可
- 示例：
  - `feat(picks): add resonance endpoint`
  - `fix(engine): handle empty df in daily_basic_cn`
  - `docs(naming): 初版命名规范落地`

---

## 9. 红线（禁止）

```ts
// ❌ snake_case 泄漏到前端
interface Item { ts_code: string; total_score: number; }

// ❌ 类型加 I / T 前缀
interface IItem {}  type TItem = {}

// ❌ 组件文件 PascalCase
ResonanceCard.tsx   // 应 resonance-card.tsx

// ❌ 股票代码字段乱起名
interface Stock { code: string }      // 应为 tsCode
interface Stock { symbol: string }    // 应为 tsCode
```

```python
# ❌ Screener.name 不是 snake_case
class MACDCrossScreener(Screener):
    name = "MACDCross"   # 应为 "macd_cross"
```

```sql
-- ❌ 跨市场表漏后缀
CREATE TABLE daily (...);   -- 应为 daily_cn

-- ❌ ingestion 文件名 ≠ 表名
engine/ingestion/sync_daily.py   -- 应为 daily_cn.py
```

---

## 10. 运行命令速查

```bash
# DB migration
cd api && pnpm migrate

# 数据同步
cd engine
uv run python -m ingestion.stocks_cn
uv run python -m ingestion.trade_cal_cn
uv run python -m ingestion.daily_cn
uv run python -m ingestion.adj_factor_cn

# 选股
uv run python -m screener.runner --date 2026-05-18

# 启动后端 / 前端
cd api && pnpm dev
cd web && pnpm dev

# 校验
cd api && pnpm typecheck && pnpm lint
cd web && pnpm typecheck && pnpm lint
```

---

## 11. AI 工作流默认要求

- 改代码前**先 grep 类似模式**（保持与现有风格一致优于发明新风格）
- 改完 TS：`pnpm typecheck` + `pnpm lint` 必须过
- 改完 Python：测试相关模块 `uv run pytest tests/test_xxx.py`
- 改完 SQL migration：本地 `pnpm migrate` 跑通；写对应 `verify_xxx.sql`
- 不确定的命名 → **查 `docs/naming-conventions.md`** 或问用户
- 跨语言契约改动（如新增策略 key、字段重命名）→ **同步改三层**，缺一不可
