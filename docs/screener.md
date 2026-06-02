# StockPulse 选股规范（v2.0）

> 详细架构 → [`architecture.md`](architecture.md) §5.1 漏斗 ｜ 命名 → [`naming-conventions.md`](naming-conventions.md) ｜ DB → [`database.md`](database.md)
> 冲突解决顺序：本文 < architecture < database < naming-conventions < 用户当次明确指示

---

## 1. 一句话

A 股短中线**多策略漏斗 + 双轴打分**：全市场 → Layer 1 通用过滤 → Layer 2 赛道粗筛 → Layer 3 多策略打分（reward + risk 双轴独立加权）→ top N 写入 `daily_picks`。

---

## 2. 全景流程图

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │ 阶段 0：数据加载（Runner 一次性预加载）                                  │
 │   ingestion 表 + indicators 表 → ScreenerData 容器                     │
 │   异常 → 整个 job FAIL                                                 │
 └──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
 ┌──────────────────────────────────────────────────────────────────────┐
 │ 阶段 1：Layer 1 通用 Filter（所有赛道共用）                              │
 │   universe = 当日有 daily 记录的 ts_code（自动剔除停牌）                 │
 │   → st_filter / new_stock_filter / low_liquidity_filter                │
 │   异常 → 整个 job FAIL                                                 │
 └──────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
 ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
 │ Track: scalp │         │ Track: swing │         │ Track: pos.. │
 ├──────────────┤         ├──────────────┤         ├──────────────┤
 │ Layer 2      │         │ Layer 2      │         │ Layer 2      │
 │ 赛道专属      │         │ 赛道专属      │         │ 赛道专属      │
 ├──────────────┤         ├──────────────┤         ├──────────────┤
 │ Layer 3      │         │ Layer 3      │         │ Layer 3      │
 │ Strategy 评分 │         │ Strategy 评分 │         │ Strategy 评分 │
 ├──────────────┤         ├──────────────┤         ├──────────────┤
 │ top_n + 落库 │         │ top_n + 落库 │         │ top_n + 落库 │
 │ (独立事务)    │         │ (独立事务)    │         │ (独立事务)    │
 └──────────────┘         └──────────────┘         └──────────────┘
   异常→该赛道 fail         异常→该赛道 fail        异常→该赛道 fail
   其他赛道继续              其他赛道继续             其他赛道继续

 → job_runs 记 ok / partial / failed
```

---

## 3. 核心抽象（5 个）

### 3.1 ScreenerData
Runner 在阶段 0 加载完所有源表后构造的**内存容器**。形态为命名空间字典：

```python
ScreenerData = {
    "daily":         pd.DataFrame,   # 当日 daily_cn 切片
    "basic":         pd.DataFrame,   # 当日 daily_basic_cn 切片
    "moneyflow":     pd.DataFrame,   # 当日 moneyflow_cn 切片
    "trend":         pd.DataFrame,   # 当日 daily_trend_indicators_cn 切片
    "momentum":      pd.DataFrame,   # 当日 daily_momentum_indicators_cn 切片
    "volume":        pd.DataFrame,   # 当日 daily_volume_indicators_cn 切片
    "moneyflow_ind": pd.DataFrame,   # 当日 daily_moneyflow_indicators_cn 切片
    "history":       pd.DataFrame,   # 历史窗口（长表，ts_code + trade_date 双索引）
    "trade_date":    date,
    "universe":      list[str],      # 当前候选 ts_code 列表（已剔除停牌）
}
```

约定：
- 当日切片以 `ts_code` 为索引。
- `history` 长度由 Runner 取所有 Strategy 的 `lookback` 最大值预加载，单只股查询通过 `data["history"].xs(ts_code)`。
- 字段名沿用 Tushare / indicators 表原始命名（snake_case），不在内存层重命名。

### 3.2 Filter
**硬过滤工具**。职责是剔除不符合基本要求的个股。

- **Layer 1（全市场）**：所有赛道共用，剔除 ST / 次新股 / 低流动性等"根本不该交易"的票。
- **Layer 2（赛道级）**：赛道专属，如 scalp 赛道要求"昨日涨停" / position 赛道要求"均线多头排列"。

Filter **不打分**，只做布尔判定（通过 / 拒绝）。

### 3.3 Strategy
**多策略打分工具**。职责是对通过前两层过滤的候选股进行**双轴量化评分**（reward + risk）。

- 输入：`PickContext`（单只股票 + 历史窗口 + 共享数据引用）
- 输出：`Scorecard` 或 `None`
- 返回 `None` = 通过 Filter 但不符合本策略的入选模型（Strategy 拥有最终否决权）

一个策略可被配置到多个赛道,但打分逻辑应保持幂等。

### 3.4 PickContext
单只股票在目标交易日的计算上下文。形态：

```python
@dataclass(frozen=True)
class PickContext:
    ts_code:    str
    trade_date: date
    daily:      pd.Series         # 当日 daily_cn 行
    basic:      pd.Series         # 当日 daily_basic_cn 行
    moneyflow:  pd.Series | None  # 当日 moneyflow_cn 行（可能不存在）
    trend:      pd.Series         # 当日 trend indicators 行
    momentum:   pd.Series         # 当日 momentum indicators 行
    volume:     pd.Series         # 当日 volume indicators 行
    moneyflow_ind: pd.Series | None
    history:    pd.DataFrame      # 该股最近 N 个交易日（N = Runner 全局 lookback 上限）
    data:       ScreenerData      # 跨股聚合需要时回查（如分位数）
```

生命周期：仅限单次 `Strategy.score()` 调用。

### 3.5 Scorecard
评分卡。Strategy 产出的结构化结果，包含双轴维度评分、权重与明细。

- **存储**：序列化为 JSONB 写入 `daily_picks.scorecard`
- **用途**：前端组件渲染"为什么入选 + 风险点 + 维度雷达图"
- **结构契约**：详见 §5

---

## 4. 双轴打分模型

### 4.1 公式

```
reward_score = Σ (reward_dim.score × reward_dim.weight)     -- reward 轴内归一
risk_score   = Σ (risk_dim.score   × risk_dim.weight)       -- risk   轴内归一
final_score  = w_reward × reward_score + w_risk × risk_score
```

### 4.2 默认值

- `w_reward = 0.70`
- `w_risk   = 0.30`
- 约束：`w_reward + w_risk ≤ 1.00`（预留未来扩展第 3 轴空间）

### 4.3 关键设计

| 设计点 | 决策 | 理由 |
|---|---|---|
| reward / risk 分离 | 独立轴打分 + 加权合成 | 不让"高收益盖过高风险"，调权重时双轴独立调 |
| risk 语义 | **风险规避分**（越高越安全） | 与 reward 同向，加权时不用符号翻转 |
| 权重存储 | DB 列 `w_reward` / `w_risk` + scorecard JSONB `axis_weights` 镜像 | 列利于 SQL 查询/排序；JSONB 利于自描述/前端渲染 |
| 数据类型 | score `NUMERIC(5,2)` / weight `NUMERIC(3,2)`，2 位小数 | 避免浮点误差，CHECK 约束严格 `≤` 而非容差 |

---

## 5. Scorecard JSONB 契约（v2.0）

### 5.1 形状

```json
{
  "axis_weights": {
    "reward": 0.70,
    "risk":   0.30
  },
  "axis_scores": {
    "reward": 86.40,
    "risk":   85.00,
    "final":  85.98
  },
  "reward_dimensions": {
    "limit_up_strength": {
      "score":   88.00,
      "weight":  0.60,
      "details": { "limit_up_count_10d": 2, "max_consecutive": 1 }
    },
    "sector_momentum": {
      "score":   84.00,
      "weight":  0.40,
      "details": { "sector_rank_pct": 0.92 }
    }
  },
  "risk_dimensions": {
    "liquidity_risk": {
      "score":   85.00,
      "weight":  1.00,
      "source":  "shared:liquidity_risk",
      "details": { "amount": 280000.0, "amount_rank_pct": 0.78 }
    }
  }
}
```

### 5.2 字段说明

| 路径 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `axis_weights.reward` | number(0~1) | ✅ | 与 DB 列 `w_reward` 镜像 |
| `axis_weights.risk`   | number(0~1) | ✅ | 与 DB 列 `w_risk`   镜像 |
| `axis_scores.reward`  | number(0~100) | ✅ | reward 轴内加权和 |
| `axis_scores.risk`    | number(0~100) | ✅ | risk 轴内加权和 |
| `axis_scores.final`   | number(0~100) | ✅ | 与 DB 列 `final_score` 镜像 |
| `reward_dimensions`   | object | ✅ | reward 轴维度集合（≥1 个） |
| `risk_dimensions`     | object | ✅ | risk 轴维度集合（≥1 个） |
| `*_dimensions.<key>.score`   | number(0~100) | ✅ | 该维度得分 |
| `*_dimensions.<key>.weight`  | number(0~1)   | ✅ | 该维度在所在轴内的权重 |
| `risk_dimensions.<key>.source` | string | ✅ | `shared:<func>` 或 `strategy:<strategy_name>` |
| `*_dimensions.<key>.details` | object | 推荐 | 维度专属明细，snake_case keys |

### 5.3 强制规则

1. 四个顶层 key (`axis_weights` / `axis_scores` / `reward_dimensions` / `risk_dimensions`) 必须存在。
2. `reward_dimensions` 与 `risk_dimensions` 各至少 1 个维度。
3. `risk_dimensions` 至少 1 个维度的 `source` 以 `shared:` 开头（本期等价必含 `shared:liquidity_risk`）。
4. 同一轴内 `Σ weight ≈ 1.0`（容差 1e-6）。
5. `axis_scores.reward` 等于 reward 轴加权和（容差 1e-6）；risk / final 同理。
6. JSONB 内部 key 全部 snake_case。
7. pulse-api repository 层负责递归 snake → camel 转换后返回前端。

### 5.4 共享 vs 策略私有 risk 维度

| 类型 | source 格式 | 实现位置 | 适用场景 |
|---|---|---|---|
| 共享 | `shared:liquidity_risk` | `pulse_core/screener/dimensions/risk.py` | 所有策略都该考虑的标准风险（流动性 / 波动 / 资金面等） |
| 策略私有 | `strategy:limit_up_replay` | Strategy 类内部方法 | 该策略独有的风险逻辑 |

本期标准共享维度仅 1 个：`liquidity_risk`（基于 `daily_basic_cn.amount` 横截面分位数）。

---

## 6. 风险维度分类（5 类）

| 类 | 名称 | 处理位置 | 本期实现 | 示例 |
|---|---|---|---|---|
| A | 硬风险（必须排除） | Layer 1 Filter | ✅ | ST / 停牌 / 次新股 / 极低流动性 |
| B | 市场结构风险 | scorecard 共享维度 | ✅(部分) | 流动性差 / 高波动 |
| C | 资金行为风险 | scorecard 共享维度 | 🚧 | 主力净流出 / 大单异常 |
| D | 策略专属风险 | scorecard 策略私有维度 | 🚧 | 涨停板"一字板"难买入 |
| E | 事件/基本面风险 | ❌ 本期盲区 | ❌ | 股东减持 / 财报暴雷 / 商誉计提 |

E 类需要新增 ingestion 表（股东数据 / 公告 / 财报），本期不实现。未来扩展时新增 `event_risk` 共享维度即可，scorecard schema 无需变更。

---

## 7. Filter 契约（Protocol）

### 7.1 接口签名

```python
from typing import Protocol
from dataclasses import dataclass

@dataclass(frozen=True)
class FilterResult:
    name:     str                    # = Filter.name
    passed:   set[str]               # 通过的 ts_code
    rejected: dict[str, dict]        # ts_code -> {"reason": str, "detail": dict}

class Filter(Protocol):
    name:        str                 # 与文件名（不含 .py）一致
    layer:       int                 # 1=通用 / 2=赛道专属
    lookback:    int = 0             # 需要的历史天数，默认 0（仅当日切片）
    description: str = ""

    def apply(self, data: ScreenerData) -> FilterResult: ...
```

### 7.2 注册与使用

- Filter 类在 `pulse_core/screener/filters/{layer}/{name}.py`
- Runner 维护 `FILTER_REGISTRY: dict[str, type[Filter]]`，YAML 中按 `name` 引用。
- 多 Filter 组合：`final_passed = reduce(set.intersection, [r.passed for r in results])`。
- `rejected` 详情本期不入库，仅用于日志 / 未来审计页 hook。

### 7.3 异常语义

- Filter 内部抛异常 → **整个赛道 FAIL**（fail-fast）。job_runs 记 error，人工排查。
- 通过的股票数为 0 不算异常，赛道正常结束（写入 0 行）。

---

## 8. Strategy 契约（Protocol）

### 8.1 接口签名

```python
class Strategy(Protocol):
    name:        str                 # 与文件名（不含 .py）一致；DB strategy 列写入此值
    lookback:    int = 0             # 需要的历史天数（Runner 取所有 Strategy 最大值预加载）
    description: str = ""

    def score(self, ctx: PickContext) -> Scorecard | None:
        """打分。返回 None 表示该股不入选本策略。"""
        ...
```

### 8.2 不入选语义

返回 `None` = 该股票虽然通过 Filter，但不符合本策略的入选模型。**Strategy 拥有最终否决权**，不要勉强凑数。

### 8.3 risk 维度组装

Strategy 在 `score()` 内可自由调用共享 risk 函数 + 自定义私有 risk：

```python
from pulse_core.screener.dimensions.risk import compute_liquidity_risk

def score(self, ctx: PickContext) -> Scorecard | None:
    if not self._is_candidate(ctx):
        return None

    reward = {
        "limit_up_strength": self._score_limit_up_strength(ctx),
        "sector_momentum":   self._score_sector_momentum(ctx),
    }
    risk = {
        "liquidity_risk": compute_liquidity_risk(ctx),   # shared:liquidity_risk
        # 未来可加 "first_board_difficulty": self._score_first_board(ctx),
    }
    return Scorecard.build(reward=reward, risk=risk, w_reward=0.70, w_risk=0.30)
```

### 8.4 顶层 score 派生

DB 列 `reward_score` / `risk_score` / `final_score` 由 Scorecard 派生写入，Strategy 不手动设置。Runner 在落库前调用 `Scorecard.validate()` 校验强制规则（§5.3），失败抛 `ValueError` → 该赛道 FAIL。

---

## 9. Runner 流程

### 9.1 执行步骤

```
阶段 0：环境准备 + 数据加载
  └─ 加载 tracks/*.yaml
  └─ 计算全局 lookback 上限 = max(strategy.lookback for all strategies)
  └─ 一次性加载 ScreenerData（含历史 lookback 窗口）
  └─ 失败 → 整个 job FAIL

阶段 1：Layer 1 通用 Filter
  └─ universe = data["daily"].index.tolist()（自动剔除停牌）
  └─ 依次执行 Layer 1 Filter，取交集
  └─ 失败 → 整个 job FAIL

阶段 2~4：每个赛道独立循环（独立事务）
  ├─ 阶段 2: Layer 2 赛道专属 Filter（基于阶段 1 输出再过滤）
  │           失败 → 该赛道 FAIL，其他赛道继续
  ├─ 阶段 3: Layer 3 Strategy 评分
  │           对剩余股票，逐只构造 PickContext，迭代调用该赛道下所有 Strategy
  │           Scorecard.validate() 失败 → 该赛道 FAIL
  │           Strategy 抛异常 → 该赛道 FAIL
  │           Strategy 返回 None → 跳过该（股，策略）组合
  └─ 阶段 4: 持久化
              按 (track, strategy) 分组排序，每组取 top_n
              DELETE WHERE trade_date = ? AND track = ? （幂等）
              INSERT 新结果
              同事务原子提交（含未来的 virtual_positions / notifications_outbox hook）

阶段 5：汇总
  └─ 写 job_runs：ok（全部赛道成功）/ partial（部分失败）/ failed（阶段 0/1 失败）
```

### 9.2 幂等性

同 `(trade_date, track)` 重跑：**先 DELETE 再 INSERT**，事务内完成。这是 architecture.md §5.3 同事务原子写规则的具体实现。

### 9.3 异常处理矩阵

| 异常位置 | 处理 | job_runs 状态 |
|---|---|---|
| 阶段 0 数据加载失败 | 整 job FAIL，无任何写入 | failed |
| 阶段 1 Layer 1 Filter 抛错 | 整 job FAIL | failed |
| 阶段 2 Layer 2 Filter 抛错 | 该赛道 FAIL，其他赛道继续 | partial |
| 阶段 3 Strategy 抛异常 | 该赛道 FAIL（不容错单只股） | partial |
| 阶段 3 Strategy 返回 None | 跳过该（股，策略），正常 | ok |
| 阶段 3 Scorecard.validate() 失败 | 该赛道 FAIL | partial |
| 阶段 4 事务提交失败 | 该赛道 FAIL，事务回滚 | partial |
| 全部赛道成功 | — | ok |

### 9.4 伪代码

```python
def run_screener(trade_date: date) -> JobResult:
    # 阶段 0
    tracks = load_tracks()                                       # tracks/*.yaml
    lookback = max(s.lookback for t in tracks for s in t.strategies)
    data = load_screener_data(trade_date, lookback=lookback)     # 失败 → 抛

    # 阶段 1
    universe = set(data["daily"].index)
    for f in LAYER1_FILTERS:
        result = f.apply(data)
        universe &= result.passed
    data["universe"] = list(universe)

    # 阶段 2~4
    per_track_status: dict[str, str] = {}
    for track in tracks:
        try:
            with db.transaction():
                # 阶段 2
                track_universe = universe.copy()
                for f in track.filters:
                    track_universe &= f.apply(data).passed

                # 阶段 3
                picks_by_strategy: dict[str, list[Pick]] = {}
                for ts_code in track_universe:
                    ctx = build_context(ts_code, data)
                    for strategy in track.strategies:
                        card = strategy.score(ctx)
                        if card is None:
                            continue
                        card.validate()                          # 强制规则
                        picks_by_strategy.setdefault(strategy.name, []).append(
                            Pick(ts_code=ts_code, scorecard=card)
                        )

                # 阶段 4
                db.execute("DELETE FROM daily_picks WHERE trade_date = %s AND track = %s",
                           (trade_date, track.name))
                for strategy_name, picks in picks_by_strategy.items():
                    top = sorted(picks, key=lambda p: p.scorecard.final, reverse=True)[:track.top_n]
                    db.bulk_insert_daily_picks(top, trade_date, track.name, strategy_name)
                    # hook: db.bulk_insert_virtual_positions(top, ...)        # 未来
                    # hook: db.enqueue_notifications_outbox(top, ...)         # 未来
            per_track_status[track.name] = "ok"
        except Exception as e:
            log.error(f"track {track.name} failed: {e}")
            per_track_status[track.name] = "failed"

    # 阶段 5
    if all(s == "ok" for s in per_track_status.values()):
        return JobResult(status="ok",      details=per_track_status)
    if any(s == "ok" for s in per_track_status.values()):
        return JobResult(status="partial", details=per_track_status)
    return JobResult(status="failed",      details=per_track_status)
```

---

## 10. Track YAML 契约

### 10.1 形状

```yaml
track:       <track_key>           # snake_case，= 文件名
description: "..."                  # 中文说明
top_n:       <int>                  # 每个 strategy 取前 N
filters:                            # Layer 2 赛道专属 Filter（按 name 引用）
  - <filter_name>
strategies:                         # 该赛道启用的 Strategy（按 name 引用）
  - <strategy_name>
```

> Layer 1 Filter 不在 YAML 中声明，由 Runner 硬编码统一执行。

### 10.2 内置赛道

#### scalp.yaml（超短赛道，本期完整骨架）

```yaml
track:       scalp
description: "超短：打板复盘 + 二次启动，1~3 日持有"
top_n:       10
filters:
  - min_price_filter          # 剔除低价股（< 3 元）
  - recent_active_filter      # 近 10 日成交活跃
strategies:
  - limit_up_replay           # 涨停复盘策略（本期示例）
```

#### swing.yaml（波段赛道，骨架占位）

```yaml
track:       swing
description: "波段：中线上行趋势中的缩量回踩，5~20 日持有"
top_n:       20
filters:
  - ma20_upward_filter        # 待实现
strategies:
  - volume_shrink_rebound     # 待实现
```

#### position.yaml（中线赛道，骨架占位）

```yaml
track:       position
description: "中线：基本面 + 趋势共振，月度持有"
top_n:       15
filters:
  - fundamental_base_filter   # 待实现
strategies:
  - trend_breakout            # 待实现
```

---

## 11. 内置组件清单（本期）

### 11.1 Layer 1 通用 Filter

| name | 数据源 | 阈值 | 说明 |
|---|---|---|---|
| `st_filter` | `stocks_cn.name` | name 含 `ST` / `*ST` / `退` | 剔除风险警示股 |
| `new_stock_filter` | `stocks_cn.list_date` | 上市未满 90 天 | 剔除次新股 |
| `low_liquidity_filter` | `daily_cn.amount` | 当日成交额 < 5000 万元 | 剔除极低流动性 |

> 停牌不需要单独 Filter：Runner 构造 `universe` 时基于 `data["daily"].index`，停牌票天然不在候选集。

### 11.2 Layer 2 赛道 Filter（scalp）

| name | 说明 |
|---|---|
| `min_price_filter` | 收盘价 < 3 元剔除 |
| `recent_active_filter` | 近 10 日有至少 1 次成交额 > 1 亿 |

### 11.3 共享 risk 维度

| 函数 | source | 数据源 | 算法 |
|---|---|---|---|
| `compute_liquidity_risk` | `shared:liquidity_risk` | `daily_basic_cn.amount` | 横截面分位数映射到 [0,100]，越流动越高分 |

### 11.4 示例 Strategy：`limit_up_replay`（涨停复盘）

**入选条件**（return None 否则）：
- 历史窗口内（近 5 个交易日）至少出现过 1 次涨停（`daily_cn.pct_chg ≥ 9.8%`）
- 当日收盘价未跌停且未涨停（留有买入空间）
- 当日成交额 ≥ 8000 万

**reward 维度**：
- `limit_up_strength`（weight 0.60）：近 10 日涨停次数 + 是否有连板，归一化到 [0,100]
- `sector_momentum`（weight 0.40）：所属行业当日涨跌幅排名分位数

**risk 维度**：
- `liquidity_risk`（weight 1.00，`source: shared:liquidity_risk`）

**轴权重**：`w_reward=0.70`, `w_risk=0.30`

**lookback**：10 个交易日

---

## 12. 红线（禁止）

- ❌ Strategy 返回 Scorecard 但 `risk_dimensions` 为空
- ❌ Scorecard 不含任何 `source: shared:...` 的 risk 维度
- ❌ Scorecard 同一轴内 weight 总和 ≠ 1.0（容差 1e-6）
- ❌ DB 列 `w_reward` / `w_risk` 与 scorecard `axis_weights` 不一致
- ❌ 绕过 `screener/runner.py` 直写 `daily_picks`（破坏 architecture.md §5.3 同事务原子性）
- ❌ Filter 在结果为空时崩溃（必须正常返回空 `FilterResult`）
- ❌ scorecard / signals JSONB 内部使用 `camelCase`（必须 snake_case）

---

## 13. 新增 checklist

### 新策略
- [ ] 在 `pulse_core/screener/strategies/{key}.py` 实现 Strategy Protocol
- [ ] `name = "{key}"`（与文件名一致）
- [ ] `score()` 内部至少组装 1 个 reward 维度 + 1 个 risk 维度
- [ ] risk 维度至少 1 个 source 以 `shared:` 开头
- [ ] 同轴 weight 总和 = 1.0
- [ ] 在某个 `tracks/{track}.yaml` 的 `strategies` 列表注册
- [ ] `pulse-web/src/lib/strategy-meta.ts` 增加元数据
- [ ] `pulse-core/tests/screener/strategies/test_{key}.py` 单元测试

### 新 Filter
- [ ] 在 `pulse_core/screener/filters/layer{1|2}/{key}.py` 实现 Filter Protocol
- [ ] `name = "{key}"`，`layer = 1 | 2`
- [ ] 返回 `FilterResult(name, passed, rejected)`
- [ ] Layer 1 → 在 Runner 的 `LAYER1_FILTERS` 注册；Layer 2 → 在 `tracks/{track}.yaml` 注册
- [ ] `pulse-core/tests/screener/filters/test_{key}.py` 单元测试

### 新共享 risk 维度
- [ ] 在 `pulse_core/screener/dimensions/risk.py` 增加 `compute_{name}_risk(ctx) -> DimensionResult`
- [ ] 在本文 §5.4 / §11.3 表格添加条目
- [ ] 至少 1 个内置 Strategy 引用它（避免孤儿维度）

### 新赛道
- [ ] 在 `pulse_core/screener/tracks/{track}.yaml` 创建
- [ ] 定义 `track` / `description` / `top_n` / `filters` / `strategies`
- [ ] `pulse-web/src/lib/track-meta.ts` 增加元数据

---

## 14. 延迟决策（TBD）

- `v_picks_resonance` 视图：等多策略落地再加
- 第 3 轴扩展（如 `event` / `momentum`）：当 E 类风险数据源落地后启用
- 风险维度 v2：`volatility_risk` / `main_flow_risk` / `position_height_risk` / `valuation_risk` / `retail_trap_risk`
- 风险维度 v3：`event_risk`（股东减持 / 财报 / 商誉，需新增 ingestion）
- virtual_positions / notifications_outbox 集成：Runner 阶段 4 留有 hook
- rejected 详情入库：当审计页落地时再启用

---

## 修订记录

| 版本 | 日期 | 说明 |
|---|---|---|
| v2.0 | 2026-06-01 | 推倒重来：reward+risk 双轴打分；scorecard 去 version/kind；shared risk 维度库；FilterResult 协议；E 类风险盲区显式声明；3 赛道 YAML 骨架 |
| v1.0 | 2026-05-x | 单轴 score + dimensions 平铺 |
