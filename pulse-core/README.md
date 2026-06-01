# pulse-core

StockPulse 计算引擎（Python + uv）：数据同步 / 指标 / 选股 / 风控 / 校验 / 权重 / 调度。

> 详细架构 → [`../docs/architecture.md`](../docs/architecture.md) §3｜调度细节 → [`../docs/scheduling.md`](../docs/scheduling.md)｜DB 设计 → [`../docs/database.md`](../docs/database.md)｜指标系统 → [`../docs/indicators.md`](../docs/indicators.md)
> 命名规则 → [`../docs/naming-conventions.md`](../docs/naming-conventions.md) §二（数据库）、§一（跨语言契约 / job_name）
> AI 守则 → [`../AGENTS.md`](../AGENTS.md)

## 技术栈

- Python 3.12+ · uv（依赖与运行环境管理）
- asyncpg（PostgreSQL 异步驱动）
- APScheduler 3.x（进程内定时器，AsyncIOScheduler）
- pandas / pandas-ta（指标计算，按需引入）
- tushare（A 股数据源）
- loguru（结构化日志）
- pytest + pytest-asyncio + ruff（测试与质量）

## 命令

> 所有命令推荐从**仓库根目录**用 pnpm 别名调用，以保持三服务一致；也可以 `cd pulse-core` 直接 `uv run`。

```bash
# 仓库根目录
pnpm core:lint                  # ruff check
pnpm core:lint:fix              # ruff check --fix
pnpm core:format                # ruff format
pnpm core:fmt                   # check --fix + format 一把过
pnpm core:test                  # pytest

# 直接在 pulse-core/ 下
uv run python -m pulse_core.ingestion.stocks_cn       # 手动同步股票列表
uv run python -m pulse_core.ingestion.daily_cn        # 手动同步日线
uv run python -m pulse_core.scheduler.daemon          # 启动常驻调度进程
uv run python -m pulse_core.screener.runner --date 2026-05-21   # 跑选股（待 screener 上线）
```

## 环境变量

环境变量集中在**仓库根** `.env`（不是子项目级）。pulse-core 关心的前缀：

- `DB_*` —— 数据库连接（host / port / user / password / database / pool_size）
- `CORE_*` —— 计算引擎自有配置（log level、APScheduler 参数等）
- `TUSHARE_TOKEN` —— Tushare 数据源 token

完整环境变量清单 → [`../docs/naming-conventions.md`](../docs/naming-conventions.md) §五。

## 目录约定

```
pulse_core/
├── lib/                          共享：db / config / logger / time / tushare_client
├── ingestion/                    Tushare 数据同步（一表一文件，文件名 = 表名）
│   ├── trade_cal_cn.py           交易日历
│   ├── stocks_cn.py              A 股列表
│   ├── daily_cn.py               日线
│   ├── adj_factor_cn.py          复权因子
│   ├── stk_limit_cn.py           涨跌停
│   ├── daily_basic_cn.py         估值
│   ├── moneyflow_cn.py           资金流
│   ├── _base.py                  ingestion 基类
│   └── _cli.py                   命令行入口共享
├── indicators/                   指标库 + 形态识别
├── screener/                     选股
│   ├── tracks/                   赛道配置（声明式 YAML）
│   ├── filters/                  过滤器（工具）
│   └── strategies/               打分策略（工具）
├── tracking/                     虚拟仓自动追踪
├── risk/                         风控扫描（卖出信号）
├── evaluation/                   策略校验
├── weights/                      权重建议
├── outbox/                       通知出箱
└── scheduler/                    任务编排
    ├── daemon.py                 常驻进程入口（持 PG advisory lock 保单实例）
    ├── cron.py                   AsyncIOScheduler 定义（到点写 pending 行）
    ├── worker.py                 轮询 job_runs 并执行 handler
    ├── registry.py               job_name → handler 注册中心
    └── jobs/                     handler 实现（一个领域一文件）
```

## 命名红线

- 模块/函数/变量 一律 `snake_case`
- 私有函数/常量 加 `_` 前缀（`_main` / `_UPSERT_SQL`）
- 类名 `PascalCase`，缩写词保留全大写（`MACDStrategy` / `ATR` / `OHLCV`）
- **ingestion 文件名 = 目标表名**（`daily_cn.py` ↔ `daily_cn` 表）
- **strategy 类名/`name` 字段 / DB `strategy` 列 / 前端 `strategy-meta.ts` key 四层完全一致**
- **job_name 三层一致**（`registry.register(...)` 的字符串 ↔ DB `job_runs.job_name` ↔ pulse-api 触发路径），详见 naming-conventions §一（跨语言契约表 / job_name 子段）
- 边界铁律：pulse-core **不开 HTTP 给前端**（前端只通过 pulse-api）；写圈 1/2/3 自动数据，不碰圈 4 用户数据

## 调度子系统

详细设计与决策依据见 [`../docs/scheduling.md`](../docs/scheduling.md)。要点：

- `scheduler/daemon.py` 是**唯一进程入口**，同时跑 AsyncIOScheduler + worker
- 单实例靠 PG advisory lock（key = `0x70756c7365646165`）保证，崩溃自动释放
- 启动时把上次崩溃残留的 `status='running'` 行回收为 `failed`
- 优雅关闭：SIGTERM/SIGINT 收到后等当前 handler 自然结束，建议部署 `stop_grace_period: 600s`
- 当前 cron 表：

  | job_name | 时刻 | 用途 |
  |---|---|---|
  | `sync_trade_cal_cn` | 18:00 | 同步交易日历 |
  | `sync_stocks_cn` | 18:02 | 同步 A 股列表（错开 2 分钟避 ORDER BY 平局） |
  | `evening_ingestion` | 18:30 | 日线/复权/涨跌停/估值/资金流 + 4 张派生指标表（6 子任务串行） |
