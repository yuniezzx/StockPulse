# StockPulse Architecture

> **目标读者：AI 助手 / 未来的自己**
> 本文是 StockPulse 架构决策的**唯一来源**。
> 命名规则 → [`naming-conventions.md`](./naming-conventions.md) ｜ AI 工作守则 → [`../AGENTS.md`](../AGENTS.md)

---

## 1. 项目定位

### 1.1 一句话目标
A 股短中线**个人**选股决策系统：每天傍晚同步数据 → 多策略漏斗选股 → 早晨推送早报 → 跟踪持仓 → 校验策略 → 调整权重。

### 1.2 做什么 / 不做什么
| ✅ 做 | ❌ 不做 |
|---|---|
| 选股、分析、买入信号、卖出风控、持仓追踪 | 回测引擎 |
| 策略效果校验、权重半自动调整 | 实盘下单、券商对接 |
| 日级 / 次日早晨级决策支持 | 盘中分钟级实时交易 |
| 单人使用、本地部署 | 多用户、SaaS、商业化 |

### 1.3 目标读者
- **第一读者：AI**。文档结构、命名、注释都以"让 AI 准确理解和修改"为最高优先级
- **第二读者：未来的自己**（几个月后回来不至于忘干净）

---

## 2. 功能版图（6 大功能）

### 2.1 闭环图
```
          ┌────────────────────────────────┐
          ▼                                │
      ② 选股 ──→ ④ 持仓 ──→ ⑤ 校验 ──→ ⑥ 权重
          ▲                                │
          └────────────────────────────────┘

      ① 股票分析（横向能力 + 独立产品页）
      ③ 风控（卖出信号，并入 ④ 持仓流）
```

### 2.2 每个功能的职责
| # | 功能 | 输入 | 输出 | 触发 |
|---|---|---|---|---|
| ① | **股票分析** | 任意 `ts_code` | 指标 + 形态 + 结论 | 用户点击 |
| ② | **选股** | 全市场 + 三赛道配置 | `daily_picks`（候选 + 共振分） | 每日定时 |
| ③ | **风控（卖出）** | 当前虚拟/真实持仓 | `risk_signals`（应卖出） | 每日定时 |
| ④ | **持仓追踪** | ② 的虚拟仓 + 用户真实仓 | 实时盈亏、最大回撤、风险标记 | 持续 |
| ⑤ | **策略校验** | ② ④ 的历史数据 | 策略胜率、夏普、最大回撤 | 每周/月 |
| ⑥ | **权重调整** | ⑤ 的校验结果 | 打分权重 + 仓位权重建议 → 用户审核 | 每周/月 |

### 2.3 ① 的双重身份
① 股票分析既是：
- **横向能力层**：为 ② ③ ⑤ 提供指标计算、形态识别
- **独立产品页**：用户输入 `ts_code` 直接查看完整分析

→ 物理实现：`pulse-core/indicators/` 作为底层库，`pulse-api/domains/analysis/` 作为查询接口。

---

## 3. 三服务架构

### 3.1 三服务定位
| 服务 | 语言 | 角色 | 写权限 |
|---|---|---|---|
| `pulse-core` | Python (uv) | 计算引擎：同步数据 + 跑策略 + 算指标 + 写自动业务数据 | 数据圈 1/2/3 |
| `pulse-api` | TypeScript (Fastify, pnpm) | API 网关 + 用户数据写入 + 通知发送 | 数据圈 4 |
| `pulse-web` | TypeScript (React+Vite, pnpm) | 前端展示 + 用户交互 | 无（零业务计算） |

### 3.2 9 条服务边界规则
```
① pulse-core 写自动数据，pulse-api 写用户数据，互不重叠
② pulse-api 不做重业务计算（薄路由 + 编排）
③ pulse-web 零业务计算(取数 + 展示)
④ pulse-core 不开 HTTP 给 pulse-web（前端只通过 pulse-api）
⑤ 用户主动触发的计算 → 提前算好走 DB（不引入 Redis）
⑥ 虚拟持仓由 pulse-core 在选股事务内创建（同事务原子写入）
⑦ 通知用 outbox 模式（pulse-core 写表，pulse-api 发）
⑧ 通知通道：企业微信群机器人(P0) + 邮件(P1) + Telegram(P2 留口子)
⑨ `job_runs` 表写权限例外：pulse-api 可 INSERT `status='pending'` 的行（用户手动触发入口），UPDATE 仍归 pulse-core worker
```

### 3.3 为什么这样切
| 切分点 | 理由 |
|---|---|
| Python 跑计算 | pandas-ta / 数据处理生态强 |
| TS 跑 API | 与前端共享类型、Fastify 性能足够 |
| 计算与 API 分进程 | 计算可独立调度，API 可独立重启 |
| 前端零计算 | 单一职责，避免业务逻辑散落 |
| 不引入 Redis | 单人项目，DB 预计算 + PG buffer 已足够 |

---

## 4. 数据流

数据圈层、写权限矩阵详见 [`database.md`](database.md) §2。

### 4.1 数据流向图
```
Tushare
   │ (ingestion)
   ▼
[圈 1 原始]──→ [圈 2 派生]──→ [圈 3 自动业务]──→ outbox
   │              │                   │              │
   │              │                   ▼              │ (api cron 扫)
   │              │            [圈 4 用户业务]       ▼
   │              │                   │         企业微信 / 邮件
   └──────────────┴───────────────────┘
                  │
                  ▼
              pulse-api ──→ pulse-web
```

### 4.2 9 条数据流规则
```
① 数据单向流动（圈层不可逆向写）
② 4 个圈层职责清晰、互不污染
③ pulse-core 写圈 1/2/3，pulse-api 写圈 4
④ 关键事务：选股 + 虚拟仓 + outbox 同事务原子写入
⑤ 通知节奏：早报聚合（scheduled_at = 次日 07:00）；运维告警（job 失败等）立即（scheduled_at = NOW()）
⑥ 通知聚合：pulse-api 发送时合并多事件为一条早报
⑦ ⑥ 权重模式：半自动（系统建议 + 用户审核确认）
⑧ 风控延迟：次日早晨级（不做盘中分钟级）
⑨ 任务可观测：所有定时/手动任务运行记录写入 `job_runs`（scheduler 写 pending，worker 跑并更新状态）
```

---

## 5. 关键机制

### 5.1 选股漏斗 × 3 赛道
```
全市场 ~5000 股
    │
    ▼ Layer 1: 通用过滤（ST/停牌/上市天数/流动性）
~3000 股
    │
    ▼ Layer 2: 赛道粗筛（成交额/波动率/趋势）
超短: ~500    波段: ~500    中线: ~500
    │             │             │
    ▼             ▼             ▼ Layer 3: 策略打分
超短策略         波段策略       中线策略
（涨停/突破等）   （回踩等）     （MACD/基本面）
    │             │             │
    ▼             ▼             ▼
                共振汇总
                    │
                    ▼
             daily_picks (top N per track)
```
**实现原则**：`screener/filters/`（过滤器）+ `screener/strategies/`（打分策略）= **工具**；`screener/tracks/`（赛道配置）= 声明式组合上面的工具；一个策略可被多个赛道复用。

→ 核心抽象（`PickContext` / `Filter` / `Strategy` / `Scorecard`）、JSONB 契约、Runner 流程详见 [`screener.md`](screener.md)。

### 5.2 买卖分离
| 行为 | 决策者 | 物理位置 |
|---|---|---|
| **买入信号** | 策略（多样化） | `pulse-core/screener/strategies/` |
| **卖出信号** | 通用风控（半自动） | `pulse-core/risk/` |

→ 同一只票，可由策略 A 买入，被通用风控规则触发卖出。

### 5.3 虚拟仓同事务
```python
async with conn.transaction():
    await insert_picks(picks)            # 1. 写 daily_picks
    await create_virtual_positions(picks) # 2. 写 virtual_positions
    await enqueue_notification(...)      # 3. 写 notifications_outbox
```
→ 三件事原子完成。

### 5.4 通知 outbox 模式
```
pulse-core                pulse-api
    ▼                         │
notifications_outbox          │
status=pending                │
scheduled_at=次日07:00        │
    └───────扫描──────────────┘
                              ▼ 07:00 cron
                          聚合多事件 → 企业微信 / 邮件 / TG → status=sent
```

### 5.5 早报聚合
一晚上可能产生 N 条事件，pulse-api 在 07:00 触发时按用户聚合 → 一封早报，内容分块：📊 今日候选 / ⚠️ 风险提示 / 📈 策略校验 / 🎯 权重建议。

### 5.6 半自动权重
```
weight_suggestions（建议）→ 用户登录 web 审核 → weight_decisions（决策）→ strategy_weights（生效）
```

---

## 6. 目录结构
```
StockPulse/
├── pulse-core/                       Python · uv · 计算引擎
│   ├── pyproject.toml
│   └── pulse_core/
│       ├── lib/                      共享：db / config / logger / time / tushare_client
│       ├── ingestion/                Tushare 数据同步（一表一文件，文件名=表名）
│       ├── indicators/               指标库（adjust / trend / momentum / volume / moneyflow）
│       ├── screener/                 选股（base / runner / tracks / filters / strategies）
│       ├── tracking/                 虚拟仓自动追踪（原 portfolio/）
│       ├── risk/                     风控扫描（卖出信号）
│       ├── evaluation/               ⑤ 策略校验
│       ├── weights/                  ⑥ 权重建议
│       ├── outbox/                   通知出箱（原 notify/）
│       └── scheduler/                任务编排（daemon / cron / worker / registry / jobs）
│
├── pulse-api/                        TypeScript · pnpm · Fastify
│   └── src/
│       ├── server.ts / config/ / adapters/db/ / plugins/
│       ├── notifier/                 扫 outbox → 发通知（briefing / channels）
│       └── domains/                  auth / picks / analysis / portfolio / virtual-portfolio
│                                     risk-signals / strategies / evaluations / preferences
│
├── pulse-web/                        TypeScript · pnpm · React + Vite
│   └── src/
│       ├── main.tsx / router/ / store/ / hooks/
│       ├── lib/                      api/ / strategy-meta / track-meta / exit-reason-meta
│       ├── pages/                    login / home / picks / analysis / portfolio
│       │                             virtual-portfolio / strategies / evaluations / settings
│       └── components/               ui/ layout/ auth/ picks/ analysis/ ...
│
├── db/migrations/
├── docs/
├── README.md / AGENTS.md / pnpm-workspace.yaml / package.json / pyproject.toml
```
**约定**：Python 目录用连字符（`pulse-core`），包名用下划线（`pulse_core`）；TypeScript 文件名一律 kebab-case（含组件文件）。

---

## 7. 技术选型

任务调度细节详见 [`scheduling.md`](scheduling.md)。

### 7.1 为什么不用 Redis
| 场景 | 替代方案 |
|---|---|
| 跨服务通信 | PG（outbox + 状态字段） |
| 缓存热数据 | PG shared_buffers（2GB 配置） |
| 异步队列 | PG outbox + APScheduler 扫描 |

**理由**：单人项目，64GB 内存还要给其他服务用，Redis 引入额外运维成本不值得。

### 7.2 硬件预算
```
总硬件: 1TB SSD + 64GB RAM
├── 操作系统 + 其他软件: ~20GB RAM
├── 用户日常软件: ~20GB RAM
└── StockPulse 可用: ~15-20GB RAM

PG 配置: shared_buffers=2GB / work_mem=64MB / effective_cache_size=8GB
数据规模: ~30GB（10 年 A 股全量）= 3% 磁盘
```

---

## 8. 延迟决策（TBD 清单）

**原则**：架构定方向，细节在编码时定。

### 8.1 9 个待定项
| # | 项 | 决策时机 |
|---|---|---|
| 1 | ① 分析结论粒度（多详细） | 写 analysis domain 时 |
| 2 | ② 漏斗 Layer 2 是否三赛道共享 | 写 screener/runner 时 |
| 3 | ③ 风控规则归属（系统级 / 策略级） | 写 risk 模块时 |
| 4 | ③ 风控规则复杂度（单规则 / 组合规则） | 写 risk 模块时 |
| 5 | ④ 持仓归档保留哪些字段 | 写 portfolio domain 时 |
| 6 | ⑤ 校验时间窗口（滚动 / 固定） | 写 evaluation 时 |
| 7 | ⑥ 权重 A 手动 / 自动比例 | 写 weights 时 |
| 8 | ⑥ 权重 A 是否分赛道 | 写 weights 时 |
| 9 | ⑥ 权重 B 仓位映射函数（线性 / 分档） | 写 weights 时 |

### 8.2 DB 表设计
- 全部延迟到编码时
- 必须严格遵循 [`naming-conventions.md`](./naming-conventions.md)

### 8.3 API 端点
- 全部延迟到编码时
- 路径风格、字段命名遵循 [`naming-conventions.md`](./naming-conventions.md)
- 一个 domain 一个文件夹（`routes / service / repository / schemas`）

---

## 9. 文档边界

| 文档 | 职责 | 不写什么 |
|---|---|---|
| `architecture.md`（本文） | 架构决策、模块边界、数据流、技术选型 | 命名规则、API 细节、表结构 |
| `naming-conventions.md` | 命名 / 字段 / SQL / 文件名规则 | 架构、业务逻辑 |
| `screener.md` | 选股子系统契约：抽象、JSONB 形状、Filter/Strategy/Scorecard 协议、Runner 流程 | 架构推导、命名规则、其他子系统 |
| `database.md` | DB 设计约定（圈层 / JSONB / 软删除 / migration / 表清单） | 架构推导、命名细节 |
| `scheduling.md` | 调度机制（APScheduler / scheduler-worker / cron 表） | 其他子系统 |
| `indicators.md` | 指标系统（列命名 / MDX 7 节格式 / 指标层职责） | 架构推导、其他子系统 |
| `AGENTS.md`（v3 重写中，当前缺位） | AI 工作守则、目录速查、checklist、命令 | 架构推导、为什么 |
| `README.md` | 一句话介绍 + 快速跑起来 + 文档导航 | 细节（全部链接到上述三份） |

**冲突解决顺序**（弱 → 强）：
```
README < AGENTS < architecture < screener < database < scheduling < indicators < naming-conventions < 用户当次明确指示
```

---

**版本**: v2.0 (refactor/v2-rebuild)
**创建**: 2026-05-21

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.1 | 2026-06-01 | 抽出 database.md / scheduling.md；修复 9 条规则编号；删除旧目录归档段与老表归档条目 |
| v2.2 | 2026-06-01 | 文档边界新增 indicators.md；冲突顺序纳入 indicators |
