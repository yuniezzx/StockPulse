# StockPulse 命名规范

> **范围**：本仓库所有代码、SQL、配置、文档、Git 提交。冲突解决顺序：AGENTS.md < architecture.md < 本文 < 用户当次明确指示。

---

## 总原则

- **DB / Python / SQL** → `snake_case`；**TypeScript** → `camelCase`；**文件名** → `kebab-case`（Python 文件 `snake_case`，SQL migration 带序号的 `snake_case`）
- 边界 1:1 对齐外部源（Tushare 原字段不重命名）
- 跨边界显式转换：`snake_case` 绝不泄漏到前端类型，转换在 `repository.ts` 层完成

---

## 一、跨语言契约表 ★

| 概念 | DB 列 | Python 标识符 | TS 标识符 | 备注 |
|---|---|---|---|---|
| 股票代码 | `ts_code` | `ts_code` | `tsCode` | 唯一称呼，禁 `code` / `symbol` |
| 交易日 | `trade_date` | `trade_date` | `tradeDate` | DB `DATE`，TS `string`（`YYYY-MM-DD`） |
| 策略 key | `strategy` | `Strategy.name` | union literal `string` | snake_case，四层完全相同 |
| 过滤器 key | `signals.filters.<key>`（JSONB 嵌套） | `Filter.name` | union literal `string` | snake_case，两层完全相同；DB 无独立 `filter` 列 |
| 赛道 key | `track` | yaml 文件名（无扩展名） | `track-meta.ts` key | snake_case，三层完全相同 |
| 打分 | `score` | `Pick.score: float` | `score: number` | 范围 0–100 |
| 信号详情 | `signals` (JSONB) | `Pick.signals: dict` | `Record<string, unknown>` | JSONB 自由结构 |
| 总分 | `total_score` | `total_score` | `totalScore` | 视图 / 查询级别聚合字段 |
| 共振数 | `strategy_count` | `strategy_count` | `strategyCount` | 聚合字段 |
| 创建时间 | `created_at` | `created_at` | `createdAt` | `TIMESTAMPTZ` ↔ ISO 字符串 |
| 任务名 | `job_name` | `job_name` | `jobName` | snake_case，registry / DB / API 三层完全相同 |

---

## 二、数据库（PostgreSQL / SQL）

### 2.1 表名

| 类别 | 规则 | 示例 |
|---|---|---|
| 市场数据表 | `{tushare_接口名}_{市场后缀}` | `daily_cn`、`adj_factor_cn`、`moneyflow_cn` |
| 结果 / 业务表 | 名词短语，`snake_case`，**不加** `_cn` | `daily_picks`、`users` |
| 视图 | `v_{用途}` | `v_picks_resonance` |
| 物化视图 | `mv_{用途}` | `mv_daily_picks_resonance` |

**市场后缀**：`_cn` = A 股。未来 `_hk` / `_us`。所有跨市场分表必须带后缀，禁裸名 `daily` / `stocks`。

### 2.2 列名

- 全部 `snake_case`
- **Tushare 原字段保留原名**：`ts_code` / `trade_date` / `pct_chg` / `turnover_rate` / `pe` / `pb` / `vol` / `amount`
- 标准元字段：`created_at` / `updated_at`（`TIMESTAMPTZ`，默认 `NOW()`）
- 布尔列：`is_xxx` / `has_xxx`，禁止 `xxx_flag`
- 时间列：日期用 `_date`，时间戳用 `_at`

### 2.3 主键 / 索引 / 约束

- **复合主键顺序**：时序明细表 `(ts_code, trade_date)`；结果表 `(trade_date, ts_code, strategy)`
- **索引**：`idx_{表}_{字段1}_{字段2}[_desc]`，例：`idx_daily_picks_date_strategy_score`
- **唯一索引**：`uq_{表}_{字段}`；**外键**：`fk_{子表}_{父表}`；**检查约束**：`ck_{表}_{字段}_{规则}`

### 2.4 Migration 文件

- 路径：`db/migrations/`，格式：`{3位序号}_{动词}_{对象}.sql`
- 动词：`create` / `alter` / `drop` / `seed` / `backfill`；序号合入主干后不可改
- 每张表 `CREATE TABLE` 上方**必须**注释：① 用途 ② 主键设计意图 ③ 单位换算

### 2.5 SQL 风格

- 关键字大写，表 / 列名小写，多列对齐书写
- 别名用单字母或语义短名：`p` for picks，`s` for stocks

---

## 三、Python（`pulse-core/`）

### 3.1 模块 / 包 / 文件

- 全部 `snake_case.py`
- ingestion 文件名 = 目标表名：`ingestion/daily_cn.py` ↔ `daily_cn` 表
- screener 策略文件名 = 策略 key：`screener/strategies/breakout.py`
- screener 过滤器文件名 = 过滤器 key：`screener/filters/liquidity.py`
- screener 赛道：`screener/tracks/{track}.yaml`
- indicators 按领域切分：`indicators/{domain}.py`，domain ∈ `trend` / `momentum` / `volume` / `moneyflow`；函数命名 `compute_{indicator}(df)`；`indicators/runner.py` 串联写入 `daily_{domain}_indicators_cn`
- 测试：`tests/test_{被测模块}.py`；私有入口：`_main()` + `if __name__ == "__main__"`

### 3.2 标识符

| 类型 | 规则 | 示例 |
|---|---|---|
| 函数 / 变量 | `snake_case` | `sync_daily_cn`、`trade_date` |
| 私有函数 / 私有常量 | `_前导下划线` | `_fetch_daily`、`_UPSERT_SQL` |
| 类 | `PascalCase` | `BreakoutStrategy`、`Pick` |
| 首字母缩写词 | 保留全大写 | `MACDCrossStrategy`、`ATR` |
| 模块级常量 | `UPPER_SNAKE_CASE` | `BREAKOUT_WINDOW`、`LOOKBACK_DAYS` |
| 类型别名 | `PascalCase` | `RowList = list[tuple]` |

### 3.3 跨语言 key 命名契约（四类一致性规则）

**Strategy（四层一致）**：

| 类名 | `name` 属性 | DB `strategy` 列 | 前端 `strategy-meta.ts` key |
|---|---|---|---|
| `BreakoutStrategy` | `"breakout"` | `"breakout"` | `"breakout"` |
| `MACDCrossStrategy` | `"macd_cross"` | `"macd_cross"` | `"macd_cross"` |

规则：类名 `{Key}Strategy`（PascalCase）；`name = "{key}"`（snake_case）；**四个值完全一致，任何不一致视为 bug**。

**Filter（两层一致）**：类名 `{Key}Filter`；`name = "{key}"`（snake_case）。例：`LiquidityFilter` / `"liquidity"`。

**Track（三层一致）**：`screener/tracks/{track}.yaml` 文件名（无扩展名）/ DB `track` 列 / 前端 `track-meta.ts` key——三者字面完全相同。内置：`scalp`（超短）/ `swing`（波段）/ `position`（中线）。

**job_name（三层一致）**：`registry.register("...", handler)` 第一个参数 / DB `job_runs.job_name` / pulse-api `POST /jobs/{job_name}/trigger` 路径段——三者字面完全相同。命名规则：
- 同步类（拉表）：`sync_{table_name}`，如 `sync_stocks_cn` ✅
- 领域批量动作：`{domain}_{action}`，如 `evening_ingestion` / `screener_runner` / `risk_scan` ✅
- 禁止：动词后置（`stocks_cn_sync` ❌）、加无意义后缀 `_job` / `_task` / `_handler`（❌）、camelCase / PascalCase（❌）；最大 64 字符

### 3.4 DataFrame 通用列名

- 原始价格列（沿用 Tushare）：`open` / `high` / `low` / `close` / `vol` / `amount` / `pre_close` / `pct_chg`
- 前复权列：`{原列名}_qfq`，例：`close_qfq`；后复权：`{原列名}_hfq`
- 指标列：`{指标名}{周期数字}` 直接拼接（不加下划线），例 `ma5`、`ema12`、`rsi6`、`atr14`
- 布尔派生列：`is_xxx` 前缀

### 3.5 异步 / 数据库访问

- 连接通过 `pulse_core.lib.db.acquire()` 上下文管理器获取
- 写操作显式使用 `async with conn.transaction()`；批量插入用 `conn.executemany`
- SQL 字符串用 `_前导下划线 + UPPER_SNAKE` 的模块级常量（如 `_UPSERT_SQL`）

### 3.6 日志

- 统一 `loguru.logger`；格式：`logger.info(f"[{name}] {message}")`
- 进度：`Progress: {i}/{n}`；区间打点用 `PROGRESS_INTERVAL` 常量

---

## 四、TypeScript（`pulse-api/` + `pulse-web/`）

### 4.1 文件名

| 类型 | 规则 | 示例 |
|---|---|---|
| 普通 ts 文件 | `kebab-case.ts` | `strategy-meta.ts`、`use-resonance.ts` |
| React 组件 | `kebab-case.tsx`（非 PascalCase） | `resonance-card.tsx` |
| 页面 | `kebab-case.tsx`，目录结构 = 路由 | `pages/picks/resonance.tsx` |
| 索引文件 | `index.ts` / `index.tsx`，仅聚合导出 | `router/index.tsx` |

### 4.2 标识符

| 类型 | 规则 | 示例 |
|---|---|---|
| 变量 / 函数 | `camelCase` | `getResonance`、`isHighlight` |
| React 组件 | `PascalCase` | `ResonanceCard` |
| Hook | `useXxx` | `useResonance` |
| Type / Interface | `PascalCase`，**不加** `I` / `T` 前缀 | `ResonanceItem`、`StrategyMeta` |
| 模块级常量 | `UPPER_SNAKE_CASE` | `SCORE_MAX` |
| 联合字符串字面量 | `snake_case`，与 DB / Python 对齐 | `"breakout" \| "limit_up"` |

### 4.3 API 边界字段

后端输出、Zod schema、前端类型统一 `camelCase`：

```ts
// ✅ 正确
interface ResonanceItem {
  tsCode: string;          // ← DB ts_code
  strategyCount: number;   // ← DB strategy_count
  totalScore: number;      // ← DB total_score
  tradeDate: string;       // ← DB trade_date
  strategies: string[];    // 数组元素是 snake_case 策略 key
  scores: Record<string, number>;
}
```

`repository.ts` 内部用 snake_case 的 row 类型（如 `ResonanceRow`），暴露给 routes / 前端的对象必须 camelCase。

### 4.4 目录组织

```
pulse-api/src/
├── domains/{name}/   routes.ts · service.ts · repository.ts · schemas.ts
├── notifier/         runner.ts · briefing.ts · channels/
└── plugins/          cors · jwt · cron

pulse-web/src/
├── pages/{feature}/
├── components/       ui/ · layout/ · auth/ · {feature}/
├── hooks/            use-xxx.ts
├── store/
└── lib/              api/{feature}.ts · {feature}-meta.ts · utils.ts
```

### 4.5 三层一致性（API → Hook → 组件）

| 层 | 命名 | 示例 |
|---|---|---|
| API 函数 | `getXxx` / `postXxx` | `getResonance` |
| Hook | `useXxx` | `useResonance` |
| 页面组件 | `XxxPage` | `ResonancePage` |
| 业务组件 | `XxxCard` / `XxxList` / `XxxTable` | `ResonanceCard` |

### 4.6 React 组件约定

- Props 类型：`{组件名}Props`，紧邻组件定义
- 默认导出仅页面组件；业务组件用具名导出
- 事件回调：props 侧 `onXxx`，内部实现 `handleXxx`

### 4.7 Zod schema 命名

- schema 变量：`{实体}Schema`（camelCase）；推导类型：`{实体}`（PascalCase）

```ts
export const resonanceItemSchema = z.object({ ... });
export type ResonanceItem = z.infer<typeof resonanceItemSchema>;
```

---

## 五、环境变量

- 全部 `UPPER_SNAKE_CASE`，按用途加前缀：`DB_*` / `API_*` / `CORE_*` / `TUSHARE_*` / `JWT_*` / `WEWORK_*` / `EMAIL_*` / `TELEGRAM_*`
- 前端公开变量必须 `VITE_` 开头
- 敏感值只放 `.env`（禁止提交），样板写 `.env.example` 并用 `your_xxx_here` 占位

---

## 六、Git 分支 / Commit

- **分支**：`{type}/{kebab-case}`，type ∈ `feature` / `fix` / `chore` / `docs` / `refactor` / `perf` / `test`
- **Commit**：`{type}({scope}): {subject}`，scope = `core` / `api` / `web` / `db` / `docs` / `infra`
- 示例：`feat(core): add macd cross strategy`、`fix(api): handle empty picks`、`docs(arch): 重构架构文档 v2`

---

## 七、反例（明确禁止）

```ts
// ❌ snake_case 泄漏到前端
interface Item { ts_code: string; total_score: number; }

// ❌ 类型加 I / T 前缀
interface IResonanceItem {}
type TResonanceItem = {}

// ❌ 组件文件 PascalCase
ResonanceCard.tsx   // 应为 resonance-card.tsx
```

```python
# ❌ Strategy name 用 camel / Pascal
class MACDCrossStrategy(Strategy):
    name = "MACDCross"   # 应为 "macd_cross"
```

```sql
-- ❌ 表名漏 _cn 后缀
CREATE TABLE daily (...);   -- 应为 daily_cn

-- ❌ ingestion 文件名与表名不一致
-- pulse-core/pulse_core/ingestion/sync_daily.py  →  应为 daily_cn.py
```

```
# ❌ 策略 key 四层不一致（任一不同都禁止）
DB:     "macd_cross"
Python: name = "MACDCross"
TS:     "MacdCross"
```

---

## 八、修订记录

| 日期 | 版本 | 变更 | 作者 |
|---|---|---|---|
| 2026-05-18 | v1.0 | 基于现有代码沉淀首版 | Atlas |
| 2026-05-21 | v2.0 | 三服务重命名；新增 Filter/Track 契约；§4.5 JSONB 边界 + §4.6 软删除；环境变量 `ENGINE_` → `CORE_` | Atlas |
| 2026-05-23 | v2.1 | 新增 §4.7 定时任务命名；§四 契约表增加 `job_name` 行 | Atlas |
| 2026-05-23 | v2.2 | §4.7 重写：拆分同步类 / 领域批量两类命名 | Atlas |
| 2026-05-31 | v2.3 | §2.1 indicators 文件约定；新增 §四点八 MDX 格式约定 | Atlas |
| 2026-06-01 | v3.0 | 重大重写：精简为纯命名规范单一职责。§四点五 JSONB 边界 / §四点六 软删除 / §四点八 MDX 格式 / §七 checklist / §九 检查与执行 / §2.4 指标列清单 均已迁出至 `.sisyphus/drafts/migrated-from-naming.md`。原 §四 跨语言契约表升级为 §一；原 §2.3/§2.3.1/§2.3.2/§4.7 合并进 §3.3。 | Atlas |
| 2026-06-01 | v3.0.1 | §一 契约表过滤器 key 行修正：DB 实际无 `filter` 列，filters 嵌在 `daily_picks.signals` JSONB 内；§3.4 删除"具体指标清单见 holdings"临时引用与 warmup 行为半句（属指标语义非命名）。 | Atlas |
