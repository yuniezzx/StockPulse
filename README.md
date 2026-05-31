# StockPulse

A 股短中线选股系统：Tushare 数据同步 → 多策略打分 → Web 展示 + 通知推送。

> **项目目标**：分析、选股、买卖（**不是回测**）。短中线为主。

> 📐 **AI 协作与命名规范**：见 [`AGENTS.md`](AGENTS.md) 与 [`docs/naming-conventions.md`](docs/naming-conventions.md)

---

## 一、技术栈与架构

### 1.1 进程组成（4 常驻 + 按需短任务）

| 进程 | 角色 | 启动方式 |
|------|------|----------|
| **Postgres** | 数据存储 | docker-compose |
| **Fastify** (`api/`) | HTTP API + 鉴权 | `pnpm dev` |
| **Vite** (`web/`) | 前端展示 | `pnpm dev` |
| **engine** (`engine/`) | 数据同步 + 选股打分 | CLI 短任务 / 未来 cron |
| **FastAPI**（未来） | 实时计算 HTTP 层 | uvicorn |

### 1.2 目录结构

```
StockPulse/
├── api/                    # Fastify backend
├── web/                    # Vite frontend
├── db/migrations/          # SQL migrations (001~)
├── engine/                 # Python 数据 + 选股引擎
│   ├── lib/                # 共享：config / db / tushare client
│   ├── ingestion/          # 数据同步：每个表一个文件
│   ├── compute/            # （待建）纯函数指标库（SMA/MACD/ATR）
│   ├── screener/           # （待建）6 个选股策略 + runner
│   ├── notify/             # （待建）通知通道
│   ├── api/                # （未来）FastAPI 实时计算
│   └── sql/                # 验证脚本
└── README.md
```

### 1.3 关键约定

- **engine/ 为 Python 项目根**：import 不带 `engine.` 前缀
- **字段名 1:1 对齐 Tushare**
- **归一化到基础单位**（元/股/%）在 ingestion 层做
- **多市场分表**：`stocks_cn` / `daily_cn` / `trade_cal_cn` / `adj_factor_cn`
- **历史起始日期写死**：`HISTORY_START_DATE = date(2023, 1, 1)`
- **ingestion 命名**：未来统一加 `_cn` 后缀（adj_factor_cn.py / daily_basic_cn.py）

---

## 二、数据层设计

### 2.1 必备数据清单（按优先级）

| 优先级 | 接口 | 表名 | 用途 | 体量预估 |
|--------|------|------|------|----------|
| ✅ Done | `pro.stock_basic` | `stocks_cn` | 股票基础信息 | 5,649 行 |
| ✅ Done | `pro.trade_cal` | `trade_cal_cn` | 交易日历（SSE + SZSE） | 1,461 × 2 |
| ✅ Done | `pro.daily` | `daily_cn` | OHLCV 日线 | 4.3M 行 |
| 🟡 In Progress | `pro.adj_factor` | `adj_factor_cn` | 复权因子（**消除除权失真**） | ~430 万 |
| 🔴 P0 必备 | `pro.daily_basic` | `daily_basic_cn` | **换手率/量比/流通市值/PE/PB** —— 短中线核心 | ~430 万 |
| 🟡 P1 强烈建议 | `pro.stk_limit` | `stk_limit_cn` | 涨跌停价（精确判断涨停） | ~430 万 |
| 🟡 P1 强烈建议 | `pro.moneyflow` | `moneyflow_cn` | 主力资金流（策略5 依赖） | ~430 万 |
| 🟢 P2 可后做 | `pro.concept` + `concept_detail` | `concept_cn` | 概念板块（策略6 依赖） | - |
| 🟢 P2 可后做 | `pro.index_daily` | `index_daily_cn` | 大盘指数（择时） | - |

### 2.2 单位归一化规则

| Tushare 原字段 | 原单位 | 入库单位 | 转换 |
|----------------|--------|----------|------|
| `vol` (daily) | 手 | 股 | × 100 |
| `amount` (daily) | 千元 | 元 | × 1000 |
| `total_mv` (daily_basic) | 万元 | 元 | × 10000 |
| `circ_mv` (daily_basic) | 万元 | 元 | × 10000 |
| `adj_factor` | 无单位 | 无单位 | 直接存 |

### 2.3 增量同步规则

- 基于 `trade_cal_cn` 回溯 **3 个交易日**（OFFSET 实现，不是自然日）
- ON CONFLICT DO UPDATE 覆盖（防订正数据丢失）
- `_SLEEP_BETWEEN_CALLS = 0.5` + `@tushare_retry` 双保险

### 2.4 复权用法（adj_factor）

```
后复权价 = 原始 close × adj_factor
前复权价 = 原始 close × adj_factor / 最新 adj_factor
```

---

## 三、选股系统设计

### 3.1 架构总览

```
trade_cal → ingestion → daily_cn / daily_basic / moneyflow / ...
                              ↓
                  compute/indicators.py（SMA/MACD/ATR）
                              ↓
        screener/{breakout, pullback, macd_cross, limit_up, moneyflow, sector_leader}
                              ↓
                  screener/runner.py（加权打分）
                              ↓
                   daily_picks 表（trade_date + ts_code + 各分数）
                       ↓                ↓
                  Web 展示          notify/ 通知
```

### 3.2 六大策略

| # | 策略 | 核心逻辑 | 依赖数据 |
|---|------|----------|----------|
| 1 | 趋势突破 | 收盘价突破 N 日新高 + 量能放大 | daily + adj_factor |
| 2 | 强势回踩 | 强势股回踩 MA20/MA60 不破 | daily + adj_factor |
| 3 | MACD 金叉 | DIF 上穿 DEA + 0 轴上方 | daily + adj_factor |
| 4 | 涨停板 | 当日涨停（区分主板/创业/科创） | daily + **stk_limit** |
| 5 | 资金流入 | 主力净流入 + 持续天数 | **moneyflow** |
| 6 | 板块龙头 | 概念板块内涨幅排名 | daily + **concept** |

### 3.3 打分规则

- 每个策略输出 **0–100 分**
- `total_score = Σ (strategy_score × weight)`
- 权重方案**待定**（候选：Atlas 给经验值 / 等权 1/6 / 用户自定义）
- 通用过滤：流通市值 < 20 亿剔除、换手率 < 1% 剔除、停牌剔除

### 3.4 daily_picks 表

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_date | DATE | PK |
| ts_code | VARCHAR(16) | PK |
| total_score | NUMERIC | 加权总分 |
| rank | INT | 当日排名 |
| score_breakout | NUMERIC | 策略1 分 |
| score_pullback | NUMERIC | 策略2 分 |
| score_macd | NUMERIC | 策略3 分 |
| score_limit_up | NUMERIC | 策略4 分 |
| score_moneyflow | NUMERIC | 策略5 分 |
| score_sector | NUMERIC | 策略6 分 |
| created_at | TIMESTAMPTZ | |

索引：`(trade_date, total_score DESC)`

### 3.5 技术指标库选型

- **pandas-ta**（已安装）
- 不用 TA-Lib（C 依赖安装坑多）
- 不自写（省 80% 时间）

### 3.6 运行模型

- **离线 cron 短任务**：19:30 拉数据 → 20:00 跑选股 → 通知推送
- **常驻 FastAPI**（未来）：前端用户点击触发实时自定义计算

---

## 四、TODO

### ✅ Done

- [x] 001 users 表
- [x] 002 stocks_cn 表 + ingestion（5,649 行）
- [x] 003 daily_cn 表 + ingestion（4.3M 行，2023-01-03 → 2026-05-13）
- [x] 004 trade_cal_cn 表 + ingestion（SSE + SZSE 各 1,461 行）
- [x] verify_daily_cn.sql（14 段验证全通过）
- [x] `HISTORY_START_DATE = date(2023, 1, 1)` 全局常量
- [x] `uv add pandas-ta`
- [x] 005 adj_factor_cn 表 + ingestion 代码

### 🟡 In Progress

- [ ] **跑 adj_factor_cn 全量同步**（预期 ~430 万行 / ~6 分钟）
- [ ] 写 verify_adj_factor_cn.sql

### 🔴 Next (P0)

- [ ] 006 daily_basic_cn 表（含 turnover_rate / volume_ratio / pe / pb / total_share / float_share / total_mv / circ_mv，**万元 → 元换算**）
- [ ] `engine/ingestion/daily_basic_cn.py`
- [ ] verify_daily_basic_cn.sql

### 🟡 Next (P1)

- [ ] 007 stk_limit_cn 表 + ingestion
- [ ] 008 moneyflow_cn 表 + ingestion
- [ ] 009 daily_picks 表

### 🟢 选股系统

- [ ] `engine/compute/indicators.py`（SMA / MACD / ATR 封装）
- [ ] `engine/screener/base.py`（策略基类）
- [ ] `engine/screener/breakout.py`（策略1）
- [ ] `engine/screener/pullback.py`（策略2）
- [ ] `engine/screener/macd_cross.py`（策略3）
- [ ] `engine/screener/limit_up.py`（策略4）
- [ ] `engine/screener/moneyflow.py`（策略5）
- [ ] `engine/screener/sector_leader.py`（策略6）
- [ ] `engine/screener/runner.py`（编排 + 打分聚合 + 写 daily_picks）

### 🟢 通知 + 自动化

- [ ] `engine/notify/`（通道待定：Telegram / Server 酱 / 邮件 / PushPlus）
- [ ] cron 自动化（19:30 数据 / 20:00 选股 / 20:30 通知）

### 🟢 Web + 实时

- [ ] Fastify `/api/picks` 接口（读 daily_picks）
- [ ] Web 选股结果页（按 total_score 排序、策略分维度筛选）
- [ ] `engine/api/main.py`（FastAPI 实时计算层）
- [ ] Fastify 转发到 FastAPI 的代理路由

### ❓ 待用户决策

- [ ] **通知通道**：Telegram / Server 酱 / 邮件 / PushPlus
- [ ] **策略权重**：Atlas 经验值 / 等权 1/6 / 自定义
- [ ] **第二批数据顺序**：daily_basic → stk_limit → moneyflow 还是其他

---

## 五、运行命令速查

```bash
# 数据库 migration
cd api && pnpm migrate

# 数据同步（engine 内）
cd engine
uv run python -m ingestion.stocks_cn
uv run python -m ingestion.trade_cal_cn
uv run python -m ingestion.daily_cn
uv run python -m ingestion.adj_factor_cn

# 后端 + 前端
cd api && pnpm dev
cd web && pnpm dev
```

---

## 六、学习资料附录

<details>
<summary>原 README 学习资料笔记（保留备查）</summary>

### 必读（已用到的核心 4 个）

1. **PostgreSQL** — https://www.postgresql.org/docs/17/tutorial.html
   - 2.3-2.10：CREATE TABLE / INSERT / SELECT / 约束基础
   - 5.4：CHECK 约束
   - 13：事务和并发控制
2. **node-postgres** — https://node-postgres.com/
   - Pool / pool.connect / Parameterized Queries / Transactions
3. **TypeScript** — https://www.typescriptlang.org/docs/handbook/intro.html
   - Generics / Modules / Narrowing / Utility Types
4. **Node.js** — https://nodejs.org/api/
   - fs/promises / path / url / Process / --env-file

### 建议看

5. **Fastify** — https://fastify.dev/docs/latest/
   - Getting Started / Routes / Validation / Plugins / Hooks
6. **Zod** — https://zod.dev/
7. **JWT** — https://jwt.io/introduction
8. **bcrypt** — https://github.com/kelektiv/node.bcrypt.js#readme

### 选读

9. ESLint Flat Config / 10. pnpm 工作区 / 11. @fastify/jwt + @fastify/cors

### 学习方法

带问题读文档，已经写过的代码就是最好的索引。

</details>
