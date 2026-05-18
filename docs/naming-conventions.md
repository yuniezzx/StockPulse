# StockPulse 命名规范

> **范围**：本仓库所有代码、SQL、配置、文档、Git 提交。
> **语气**：约定优于配置；不一致即视为 bug。
> **修订**：变更需在 PR 中显式说明，并同步更新本文与 `AGENTS.md`（若存在）。

---

## 总原则

**"边界 1:1 对齐外部源；内部统一语言习惯；跨边界处显式转换。"**

- **数据库 / Python / SQL** → `snake_case`（对齐 Tushare 与 SQL 习惯）
- **TypeScript / JavaScript（`api/` + `web/`）** → `camelCase`
- **跨边界转换发生在 API repository 层**：snake_case 绝不泄漏到前端类型
- **保留字段名与 Tushare 1:1 对齐**（不重命名 Tushare 原字段）
- **文件名默认 `kebab-case`**；Python 文件用 `snake_case`；SQL migration 用带序号的 `snake_case`

---

## 一、数据库（PostgreSQL / SQL）

### 1.1 表名

| 类别 | 规则 | 示例 |
|---|---|---|
| 市场数据表 | `{tushare_接口名}_{市场后缀}` | `daily_cn`、`adj_factor_cn`、`stk_limit_cn`、`moneyflow_cn`、`daily_basic_cn` |
| 结果 / 业务表 | 名词短语，`snake_case`，**不加** `_cn`（系统内部产物，与外部源无关） | `daily_picks`、`users` |
| 视图 | `v_{用途}` | `v_picks_resonance` |
| 物化视图 | `mv_{用途}` | `mv_daily_picks_resonance` |

**市场后缀约定**：`_cn` = 中国 A 股。未来扩展：`_hk`（港股）、`_us`（美股）。
**所有跨市场分表必须带后缀**，禁止用裸名 `daily` / `stocks`。

### 1.2 列名

- 全部 `snake_case`
- **Tushare 原字段保留原名**：`ts_code` / `trade_date` / `pct_chg` / `turnover_rate` / `pe` / `pb` / `total_mv` / `circ_mv` / `vol` / `amount`
- 标准元字段：`created_at` / `updated_at`（类型 `TIMESTAMPTZ`，默认 `NOW()`）
- 布尔列：`is_xxx` / `has_xxx`，禁止 `xxx_flag`
- 时间列：日期类用 `_date`，时间戳类用 `_at`

### 1.3 主键 / 索引 / 约束

- **复合主键顺序**：按查询习惯，粒度从大到小
  - 时序明细表：`(ts_code, trade_date)` —— 单股纵向查询为主
  - 结果表：`(trade_date, ts_code, strategy)` —— 按日横向查询为主
- **索引命名**：`idx_{表}_{字段1}_{字段2}[_desc]`
  - 例：`idx_daily_picks_date_strategy_score`、`idx_daily_picks_ts_code`
- **唯一索引**：`uq_{表}_{字段}`
- **外键约束**：`fk_{子表}_{父表}`
- **检查约束**：`ck_{表}_{字段}_{规则}`，例：`ck_daily_picks_score_range`

### 1.4 Migration 文件

- 路径：`db/migrations/`
- 格式：`{3位序号}_{动词}_{对象}.sql`
- 动词：`create` / `alter` / `drop` / `seed` / `backfill`
- 序号一旦合入主干**不可改**，新增只能往后递增
- 示例：
  - `009_create_daily_picks.sql`
  - `010_alter_daily_picks_add_rank.sql`
  - `011_backfill_daily_picks_signals.sql`

### 1.5 表头注释（强制）

每张表 migration 文件**必须**在 `CREATE TABLE` 上方写：

1. **用途**：一两句话说明这张表是什么、给谁用
2. **主键设计意图**：为什么是这个组合、查询模式
3. **单位约定**（数据表必备）：Tushare 原单位 → 入库单位的换算

参考样板：`db/migrations/003_create_daily_cn.sql`、`db/migrations/009_create_daily_picks.sql`。

### 1.6 SQL 风格

- 关键字大写：`SELECT` / `FROM` / `WHERE` / `JOIN`
- 表 / 列名小写
- 多列对齐书写，可读性优先
- 别名用单字母或语义短名：`p` for picks、`s` for stocks

---

## 二、Python（`engine/`）

### 2.1 模块 / 包 / 文件

- 全部 `snake_case.py`
- **ingestion 文件名 = 目标表名**：`ingestion/daily_cn.py` ↔ `daily_cn` 表
- **screener 文件名 = 策略 key**：`screener/breakout.py` ↔ `name = "breakout"`
- 测试文件：`tests/test_{被测模块}.py`
- 私有脚本入口：`_main()` + `if __name__ == "__main__"`

### 2.2 标识符

| 类型 | 规则 | 示例 |
|---|---|---|
| 函数 / 变量 | `snake_case` | `sync_daily_cn`、`trade_date`、`fetch_trading_days` |
| 私有函数 / 私有常量 | `_前导下划线` | `_fetch_daily`、`_df_to_rows`、`_UPSERT_SQL`、`_main` |
| 类 | `PascalCase` | `BreakoutScreener`、`Pick`、`Screener` |
| **首字母缩写词** | **保留全大写**（可读性优先于 PEP 8 严格 PascalCase） | `MACDCrossScreener`、`ATR`、`RSI`、`OHLCV` |
| 模块级常量 | `UPPER_SNAKE_CASE` | `BREAKOUT_WINDOW`、`SLEEP_BETWEEN_CALLS`、`LOOKBACK_DAYS`、`HISTORY_START_DATE` |
| 类型别名 | `PascalCase` | `RowList = list[tuple]` |

### 2.3 Screener 命名契约（**跨语言 contract**）

- **类名**：`{策略名 PascalCase}Screener`
- **类属性 `name`**：snake_case，作为跨 DB / API / 前端的**唯一策略 key**

| 类名 | `name` | DB `daily_picks.strategy` | 前端 `strategy-meta.ts` key |
|---|---|---|---|
| `BreakoutScreener` | `"breakout"` | `"breakout"` | `"breakout"` |
| `PullbackScreener` | `"pullback"` | `"pullback"` | `"pullback"` |
| `MACDCrossScreener` | `"macd_cross"` | `"macd_cross"` | `"macd_cross"` |
| `LimitUpScreener` | `"limit_up"` | `"limit_up"` | `"limit_up"` |
| `MoneyflowScreener` | `"moneyflow"` | `"moneyflow"` | `"moneyflow"` |
| `SectorLeaderScreener` | `"sector_leader"` | `"sector_leader"` | `"sector_leader"` |

**四个值必须完全一致**，任何不一致都视为 bug。

### 2.4 pandas DataFrame 列名

- 原始价格列（沿用 Tushare）：`open` / `high` / `low` / `close` / `vol` / `amount` / `pre_close` / `change` / `pct_chg`
- 前复权列：`{原列名}_qfq`，例：`close_qfq` / `high_qfq` / `low_qfq`
- 后复权列（如需）：`{原列名}_hfq`
- 指标列：小写简称
  - 均线：`ma5` / `ma10` / `ma20` / `ma60`（**指标名 + 周期数字直接拼接**，不要 `ma_20`）
  - MACD：`dif` / `dea` / `hist`
  - 其他：`rsi14` / `atr14`
  - 量能：`vol_ma5` / `vol_ratio_5`

### 2.5 异步 / 数据库访问

- 数据库连接通过 `lib.db.acquire()` 上下文管理器获取
- 写操作显式使用 `async with conn.transaction()`
- 批量插入用 `conn.executemany`，单行用 `conn.execute`
- SQL 字符串用 `_前导下划线 + UPPER_SNAKE` 命名的模块级常量（如 `_UPSERT_SQL`）

### 2.6 日志

- 统一使用 `loguru.logger`
- 格式：`logger.info(f"[{name}] {message}")`（`name` 为策略 / 模块标识）
- 进度日志：`Progress: {i}/{n}` 风格，区间打点用 `PROGRESS_INTERVAL` 常量

---

## 三、TypeScript（`api/` + `web/`）

### 3.1 文件名

| 类型 | 规则 | 示例 |
|---|---|---|
| 普通 ts 文件 | `kebab-case.ts` | `strategy-meta.ts`、`use-resonance.ts` |
| React 组件文件 | `kebab-case.tsx`（**不是** PascalCase） | `resonance-card.tsx`、`app-sidebar.tsx` |
| 页面 | `kebab-case.tsx`，目录结构 = 路由结构 | `pages/picks/resonance.tsx` |
| 测试 | `*.test.ts` / `*.spec.ts` | （预留） |
| 索引文件 | `index.ts` / `index.tsx`，仅用于聚合导出 | `router/index.tsx` |

### 3.2 标识符

| 类型 | 规则 | 示例 |
|---|---|---|
| 变量 / 函数 | `camelCase` | `getResonance`、`fetchData`、`isHighlight` |
| React 组件 | `PascalCase` | `ResonanceCard`、`AppSidebar` |
| Hook | `useXxx`（camelCase） | `useResonance`、`useMobile` |
| Type / Interface | `PascalCase`，**不加** `I` / `T` 前缀 | `ResonanceItem`、`StrategyMeta`、`ResonanceCardProps` |
| Zod schema 变量 | `xxxSchema`（camelCase） | `resonanceItemSchema`、`resonanceResponseSchema` |
| Zod 推导类型 | `PascalCase`，与 schema 同根 | `type ResonanceItem = z.infer<typeof resonanceItemSchema>` |
| 模块级常量 | `UPPER_SNAKE_CASE` | `SCORE_MAX`、`MIN_STRATEGIES` |
| 联合字符串字面量（枚举值） | `snake_case`，与 DB / Python 对齐 | `"breakout" \| "limit_up" \| ...` |

### 3.3 API 边界字段命名（**最重要的一条**）

后端 API 输出、Zod schema、前端类型 **统一 camelCase**：

```ts
// ✅ 正确
interface ResonanceItem {
  tsCode: string;          // ← DB ts_code
  strategyCount: number;   // ← DB strategy_count
  totalScore: number;      // ← DB total_score
  tradeDate: string;       // ← DB trade_date
  strategies: string[];    // 内部数组元素是 snake_case 策略 key
  scores: Record<string, number>;
}
```

**转换层**：`api/src/domains/{feature}/repository.ts` 或 `service.ts`
- repository 内部用 snake_case 的 row 类型（如 `ResonanceRow`）
- 暴露给 routes / 前端的对象必须 camelCase（如 `ResonanceItem`）

**业务保留键**：股票代码字段统一叫 `tsCode`，**不要** `code` / `symbol` / `stockCode`。与 Tushare 术语保持一致。

### 3.4 目录组织

**API（domain-driven）**：
```
api/src/
├── server.ts
├── config/                # 配置 / 环境变量校验
├── plugins/               # Fastify 插件（cors、jwt 等）
├── adapters/              # 外部资源适配（db pool、redis 等）
└── domains/{name}/        # 每个业务域一个目录
    ├── routes.ts          # HTTP 路由（薄，只做参数校验 + 调 service）
    ├── service.ts         # 业务逻辑
    ├── repository.ts      # 数据访问（snake_case row → camelCase entity 转换在此层）
    └── schemas.ts         # Zod schemas + 导出类型
```

**Web（feature-driven）**：
```
web/src/
├── main.tsx
├── router/                # 路由配置
├── pages/{feature}/       # 路由页面
├── components/
│   ├── ui/                # shadcn 原子组件，禁止业务逻辑
│   ├── layout/            # 布局组件（sidebar、header）
│   ├── auth/              # 认证守卫
│   └── {feature}/         # 业务组件，按 feature 分组
├── hooks/                 # 自定义 hook，文件名 use-xxx.ts
├── store/                 # zustand store
├── lib/
│   ├── api/               # API 调用层，一个 feature 一文件
│   ├── utils.ts           # cn() 等通用工具
│   └── {feature}-meta.ts  # feature 元数据（如 strategy-meta.ts）
└── types/                 # 跨 feature 共享类型
```

### 3.5 三层一致性（API → Hook → 组件）

| 层 | 命名 | 示例 |
|---|---|---|
| API 函数 | `getXxx` / `postXxx` / `putXxx` / `deleteXxx` | `getResonance` |
| Hook | `useXxx`（与 API 同名去掉动词） | `useResonance` |
| 页面组件 | `XxxPage` | `ResonancePage` |
| 业务组件 | `XxxCard` / `XxxBadge` / `XxxList` / `XxxTable` | `ResonanceCard`、`StrategyBadge` |

### 3.6 React 组件约定

- 组件 props 类型：`{组件名}Props`，紧邻组件定义
- 默认导出仅页面组件 (`export default function XxxPage`)，业务组件用具名导出
- 组件内部小组件（仅用于本文件）：直接定义函数，不抽出文件，例：`LoadingGrid`、`ErrorState`、`EmptyState`
- 事件回调命名：`onXxx`（props 接收侧）、`handleXxx`（组件内部实现侧）

### 3.7 Zod schema 命名

- schema 变量：`{实体}Schema`（camelCase）
- 推导的 TypeScript 类型：`{实体}`（PascalCase）
- 错误码字符串：`PascalCase`，例：`"ValidationError"`、`"InternalServerError"`

```ts
export const resonanceItemSchema = z.object({ ... });
export type ResonanceItem = z.infer<typeof resonanceItemSchema>;
```

---

## 四、跨语言契约（核心字段对照表）

| 概念 | DB 列 | Python 标识符 | TS 标识符 | 备注 |
|---|---|---|---|---|
| 股票代码 | `ts_code` | `ts_code` | `tsCode` | **统一称呼**，禁止 `code` / `symbol` |
| 交易日 | `trade_date` | `trade_date` | `tradeDate` | DB 为 `DATE`，TS 为 `string`（`YYYY-MM-DD`） |
| 策略 key | `strategy` | `Screener.name` | union literal `string` | snake_case，三层完全相同 |
| 打分 | `score` | `Pick.score: float` | `score: number` | 范围 0–100 |
| 信号详情 | `signals` (JSONB) | `Pick.signals: dict` | `Record<string, unknown>` | JSONB 自由结构 |
| 总分 | `total_score`（聚合产生） | `total_score` | `totalScore` | 视图 / 查询级别字段 |
| 共振数 | `strategy_count`（聚合产生） | `strategy_count` | `strategyCount` | |
| 创建时间 | `created_at` | `created_at` | `createdAt` | `TIMESTAMPTZ` ↔ ISO 字符串 |

---

## 五、环境变量

- 全部 `UPPER_SNAKE_CASE`
- 按用途加前缀：
  - `DB_*` 数据库
  - `API_*` Fastify 后端
  - `ENGINE_*` Python engine
  - `TUSHARE_*` Tushare 客户端
  - `JWT_*` 鉴权
- 前端公开变量（Vite）必须以 `VITE_` 开头
- 敏感值（token、密码）只放 `.env`，**禁止**提交；样板写在 `.env.example` 并用 `your_xxx_here` 占位

---

## 六、Git 分支 / Commit

### 6.1 分支

- 格式：`{type}/{kebab-case-description}`
- type ∈ `feature` / `fix` / `chore` / `docs` / `refactor` / `perf` / `test`
- 示例：
  - `feature/picks-resonance`
  - `fix/daily-basic-unit-scale`
  - `refactor/ingestion-base`

### 6.2 Commit（Conventional Commits）

- 格式：`{type}({scope}): {subject}`
- `type`：`feat` / `fix` / `chore` / `docs` / `refactor` / `perf` / `test` / `build` / `ci`
- `scope`：顶层目录名 —— `api` / `web` / `engine` / `db` / `notify` / `infra` / `docs`
- `subject`：中文或英文皆可，**祈使语气**，不加句号
- 示例：
  - `feat(picks): add resonance endpoint`
  - `fix(engine): handle empty df in daily_basic_cn`
  - `chore(db): add 010 migration for daily_picks.rank`
  - `docs(naming): 初版命名规范落地`

---

## 七、新增 checklist

### 7.1 新增数据表（以 `xxx_cn` 为例）

- [ ] `db/migrations/0YY_create_xxx_cn.sql`
- [ ] 表头写清用途 + 主键意图 + 单位换算
- [ ] `engine/ingestion/xxx_cn.py`（**同名**）
- [ ] `engine/sql/verify_xxx_cn.sql`
- [ ] `README.md` 数据清单表更新（优先级 / 体量预估）
- [ ] 若有跨表 JOIN：在 ingestion 的 SELECT 中保持列序、命名一致

### 7.2 新增选股策略

- [ ] `engine/screener/{strategy_key}.py`
- [ ] 类名 `{StrategyKeyPascalCase}Screener`，`name = "{strategy_key}"`
- [ ] `engine/screener/runner.py` 的 `SCREENERS` 列表注册
- [ ] `engine/tests/test_{strategy_key}.py`
- [ ] `web/src/lib/strategy-meta.ts` 增加 key 为 `{strategy_key}` 的元数据条目（label / description / badgeClass / barClass）
- [ ] DB 不需改 schema（`daily_picks.strategy` 是字符串列）
- [ ] 验证：`SELECT DISTINCT strategy FROM daily_picks` 应能查到新值

### 7.3 新增 API 端点

- [ ] `api/src/domains/{feature}/`：补 routes / service / repository / schemas
- [ ] Zod schema 字段 camelCase，repository 负责 snake → camel 转换
- [ ] `web/src/lib/api/{feature}.ts`：导出 `getXxx` / `postXxx` 等函数
- [ ] `web/src/types/{feature}.ts`：导出对应 TS 类型（**与后端 Zod 推导类型保持字段一致**）
- [ ] `web/src/hooks/use-{feature}.ts`：封装数据获取
- [ ] 页面：`web/src/pages/{feature}/{view}.tsx`

---

## 八、反例（明确禁止）

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
# ❌ Screener 类属性 name 用 camel / Pascal
class MACDCrossScreener(Screener):
    name = "MACDCross"   # 应为 "macd_cross"
```

```sql
-- ❌ 表名漏 _cn 后缀
CREATE TABLE daily (...);   -- 应为 daily_cn

-- ❌ ingestion 文件名与表名不一致
-- 文件：engine/ingestion/sync_daily.py
-- 表名：daily_cn
-- → 应改为 engine/ingestion/daily_cn.py
```

```
# ❌ 策略 key 三层不一致（任何一处不同都禁止）
DB:     "macd_cross"
Python: name = "MACDCross"
TS:     "MacdCross"
```

---

## 九、检查与执行

- **CI 层面**（按需补）：`eslint` / `tsc --noEmit` / `ruff check` / `mypy`
- **Review 必查**：
  1. 新增字段是否泄漏 snake_case 到前端
  2. 新增策略 key 三层是否一致
  3. 新增表是否带正确的市场后缀
  4. migration 表头注释是否齐全（用途 / 单位）
- **违规处理**：在 PR 中直接 block，引用本文对应小节

---

## 十、修订记录

| 日期 | 版本 | 变更 | 作者 |
|---|---|---|---|
| 2026-05-18 | v1.0 | 基于现有代码沉淀首版 | Atlas |
