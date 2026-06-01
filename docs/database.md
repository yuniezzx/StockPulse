# StockPulse 数据库设计约定

> **本文是 StockPulse DB 设计的唯一来源。**
> 命名规则（表名 / 列名 / 索引命名）→ [`naming-conventions.md`](naming-conventions.md)；
> 架构总览（服务边界 / 数据流向图）→ [`architecture.md`](architecture.md)。

---

## 1. 设计原则

- 单一存储：PostgreSQL 是唯一持久层，不引 Redis / 消息队列
- 圈层不可逆：数据单向从圈 1 流向圈 4，低圈层不写高圈层
- 结构优先：能建列就建列，JSONB 仅作逃生舱
- 软删除克制：能硬删就硬删，软删除仅用于需要历史的少数业务表
- 可观测：所有定时 / 手动任务运行结果写入 `job_runs`

---

## 2. 数据圈层

### 2.1 4 个数据圈层

```
┌─ 圈 1 原始数据（Tushare 同步）
│   └─ stocks_cn / daily_cn / adj_factor_cn / daily_basic_cn / trade_cal_cn
│
├─ 圈 2 派生数据（指标 + 复权）
│   └─ 由 pulse-core 计算（部分入库，部分实时算）
│
├─ 圈 3 自动业务数据（策略产出）
│   └─ daily_picks / virtual_positions / risk_signals
│   └─ evaluations / weight_suggestions / notifications_outbox
│
└─ 圈 4 用户业务数据（人工录入/审核）
    └─ users / real_positions / strategy_weights / preferences
    └─ weight_decisions（审核记录）
```

### 2.2 写权限矩阵

| 圈层 | 写者 | 读者 |
|---|---|---|
| 圈 1 | pulse-core（ingestion） | pulse-core / pulse-api |
| 圈 2 | pulse-core（indicators） | pulse-core / pulse-api |
| 圈 3 | pulse-core（screener/risk/evaluation/weights） | pulse-core / pulse-api |
| 圈 4 | pulse-api（用户请求） | pulse-core / pulse-api |

---

## 3. JSONB 使用边界

**原则**：JSONB 是"逃生舱"，不是默认存储。**结构化的、要查询的、要校验的字段必须升列**。

### 3.1 何时用 JSONB（✅）

- **策略 signals 详情**：每个策略输出的中间值（如 MACD 的 `dif/dea/hist`），结构因策略而异
- **校验报告快照**：`evaluations.report`（每次校验跑完一份完整快照，结构会演进）
- **通知 payload**：`notifications_outbox.payload`（不同事件结构不同）
- **用户偏好**：`preferences.config`（个性化字段集合）
- **风控触发上下文**：`risk_signals.context`（触发时的快照数据）

### 3.2 何时禁止 JSONB（❌）

- 任何需要 `WHERE` / `ORDER BY` / `JOIN` 的字段
- 任何有固定枚举值的字段（如 `strategy` / `track` / `status`）
- 任何统计需要的数值字段（`score` / `pnl` / `weight`）
- 任何外键引用

### 3.3 JSONB 字段命名

- 列名以 `_data` / `_payload` / `_context` / `_config` / `_report` / `_signals` 结尾
- JSONB **内部 key** 仍用 `snake_case`（与 DB 风格统一）
- 进入 TS 后整个 JSONB 块用 `Record<string, unknown>` 接收，业务侧再窄化

```ts
// ✅ snake_case 在 JSONB 内部允许（DB 内部约定）
const signals = { macd_dif: 0.5, vol_ratio: 1.8 };

// JSONB 字段映射到 TS：键名 camelCase 化只在"显式提取"时做
interface PickDetail {
  signals: Record<string, unknown>;  // 透传，不做键名转换
}
```

---

## 4. 软删除规则

**原则**：能硬删就硬删。仅以下场景启用软删除。

### 4.1 何时软删除（`deleted_at TIMESTAMPTZ`）

- 用户真实持仓：清仓后保留历史（`real_positions.deleted_at`）
- 虚拟持仓：退出后归档（`virtual_positions.deleted_at`）
- 用户审核记录：永久保留（`weight_decisions` 用 `status` 字段替代软删除）

### 4.2 软删除字段命名

- 列名固定 `deleted_at`，类型 `TIMESTAMPTZ NULL`
- 配套查询视图：`v_{表}_active`（自动过滤 `WHERE deleted_at IS NULL`）
- 所有 SELECT **默认** 加 `WHERE deleted_at IS NULL`，需要全量时显式写 `INCLUDE deleted`

### 4.3 自动数据不软删

圈 1/2/3 的自动数据（`daily_cn` / `daily_picks` / `risk_signals` 等）**禁止**软删除：
- 重跑覆盖（`ON CONFLICT DO UPDATE`）或硬删重写
- 历史数据用归档表（`{表}_archive`），不用 `deleted_at`

---

## 5. Migration 约定

### 5.1 文件命名

- 路径：`db/migrations/`，格式：`{3位序号}_{动词}_{对象}.sql`
- 动词：`create` / `alter` / `drop` / `seed` / `backfill`
- 序号合入主干后**不可改**

### 5.2 表头注释要素

每张表 `CREATE TABLE` 上方必须注释：

```sql
-- 用途：XXX（一句话说明这张表存什么）
-- 主键设计意图：XXX（为什么这样设 PK / 唯一约束）
-- 单位换算：XXX（金额单位 / 比例单位等，无则写"无特殊单位"）
```

### 5.3 配套 verify SQL

每个 migration 建议附 verify 查询，用于确认建表 / 迁移结果：

```sql
-- verify
SELECT COUNT(*) FROM information_schema.tables
WHERE table_name = '{表名}';
```

### 5.4 Review 必查

- migration 表头注释是否齐全（用途 / 单位）
- 新增表是否带正确的市场后缀（`_cn`）
- 新增字段是否遵循软删除 / JSONB 规则

---

## 6. 表清单速查

### 圈 1：原始数据

| 表名 | 用途 |
|---|---|
| `stocks_cn` | A 股股票基础信息（代码 / 名称 / 上市状态） |
| `daily_cn` | A 股日线行情（OHLCV） |
| `adj_factor_cn` | 复权因子 |
| `daily_basic_cn` | 每日基本面指标（PE / PB / 换手率等） |
| `trade_cal_cn` | 交易日历 |
| `stk_limit_cn` | 涨跌停数据 |
| `moneyflow_cn` | 主力资金流向 |

### 圈 2：派生数据（指标）

| 表名 | 用途 |
|---|---|
| `daily_trend_indicators_cn` | 均线 / MACD 等趋势指标 |
| `daily_momentum_indicators_cn` | RSI / ATR / 涨跌幅等动量指标 |
| `daily_volume_indicators_cn` | 量比 / 换手率均线等量能指标 |
| `daily_moneyflow_indicators_cn` | 主力资金派生指标 |

### 圈 3：自动业务数据

| 表名 | 用途 |
|---|---|
| `daily_picks` | 选股策略每日输出（候选股 + 信号详情） |
| `job_runs` | 所有定时 / 手动任务运行流水（状态 / 耗时） |

### 圈 4：用户业务数据

| 表名 | 用途 |
|---|---|
| `users` | 用户账号（系统初期单用户） |

> 圈 3/4 其余表（`virtual_positions` / `risk_signals` / `evaluations` / `weight_suggestions` / `notifications_outbox` / `real_positions` / `strategy_weights` / `preferences` / `weight_decisions`）migration 尚未落地，表名来自 architecture §4.1 设计意图。

---

## 修订记录

| 版本 | 日期 | 说明 |
|---|---|---|
| v1.0 | 2026-06-01 | 从 architecture / naming holdings 抽出独立成文 |
