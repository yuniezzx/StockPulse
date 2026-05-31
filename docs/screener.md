# StockPulse 选股规范

> 详细架构 → architecture.md §5.1 漏斗 ｜ 命名 → naming-conventions.md
> 冲突解决顺序：本文 < architecture < naming-conventions < 用户当次明确指示

## 1. 一句话
A 股短中线多策略漏斗：全市场 → Layer 1 通用过滤 → Layer 2 赛道粗筛 → Layer 3 多策略打分 → top N 写入 daily_picks。

## 2. 核心抽象（4 个）

### 2.1 PickContext
单只股票在目标交易日的计算上下文快照。包含：
- **行情快照**：当日开高低收、成交量、成交额、复权因子。
- **派生指标**：`daily_trend_indicators_cn`、`daily_momentum_indicators_cn` 等表的对应行。
- **历史记录**：可选的 N 日回溯窗口数据（由 runner 根据策略需求注入）。
- **信号日志**：累积记录该股票在 Layer 1/2 被 Filter 命中时的中间参数。
数据归属于 `pulse-core` 内存对象，生命周期仅限于单次选股任务。

### 2.2 Filter
硬过滤工具。职责是剔除不符合基本要求的个股。
- **Layer 1（全市场）**：剔除 ST、停牌、上市未满一年的次新股、日均成交额低于 5000 万的僵尸股。
- **Layer 2（赛道级）**：根据赛道特性过滤，如超短赛道过滤非涨停股，中线赛道过滤低价股。
Filter 操作 `pd.DataFrame`，输入输出格式由 §8 契约定义。

### 2.3 Strategy
多策略打分工具。职责是对通过前两层过滤的候选股进行量化评分。
- **输入**：`PickContext`（单行）。
- **输出**：`Scorecard` 对象。若返回 `None` 则表示虽然通过了 Filter 但不符合该策略的入选模型。
一个策略可被配置到多个赛道中，但打分逻辑应保持幂等。

### 2.4 Scorecard
评分卡。策略产出的结构化结果，包含维度评分、权重与明细。
- **存储**：序列化为 JSONB 写入 `daily_picks` 表。
- **用途**：前端组件渲染选股理由、风险等级、维度分布图。
- **结构契约**：详见 §4。

## 3. 数据流形态
Runner 采用"批量读取 + 流式计算"的折中模式以平衡开发效率与运行性能：
1. **数据准备**：从数据库一次性加载全市场当日所有必要指标。
2. **向量化过滤**：在 DataFrame 上利用 pandas 的 `loc` 或 `query` 执行通用过滤。
3. **上下文分发**：runner 对每只候选股切出对应的 `PickContext`（单行视图），逐一传给 Strategy。具体迭代方式（itertuples / iterrows / 自定义包装）属于实现细节，不在本契约约束。
4. **多策略评分**：迭代调用配置在该赛道下的所有 Strategy 实例。
5. **同事务提交**：聚合所有 Strategy 产出的 Picks，开启事务原子写入 `daily_picks` 及关联表。

## 4. Scorecard JSONB 契约（v1.0）
严格遵循 `db/migrations/014_create_daily_picks.sql` 定义。

```json
{
  "version": "1.0",
  "dimensions": {
    "trend": {
      "score": 85.0,
      "weight": 0.4,
      "kind": "reward",
      "details": { "ma20_slope": 0.05, "distance_to_ma5": 0.02 }
    },
    "volatility": {
      "score": 60.0,
      "weight": 0.3,
      "kind": "risk",
      "details": { "atr_20d_pct": 0.06 }
    },
    "liquidity": {
      "score": 90.0,
      "weight": 0.3,
      "kind": "risk",
      "details": { "turnover_rate_5d": 0.035 }
    }
  }
}
```

**字段说明**：
- `dimension_key`：使用 `snake_case`，如 `momentum` / `fundamental` / `risk_control`。
- `kind`：枚举值 `"reward"` 或 `"risk"`。
- `score`：数值 [0, 100]，统一遵循"越高越好"原则。
- `weight`：数值 [0, 1.0]，同一 Scorecard 内所有 dimensions 的 weight 之和必须等于 1.0。
- `details`：内部结构由 Strategy 定义，仅限 `snake_case` 键。

## 5. signals JSONB 契约
记录漏斗累积日志，用于调试、审计与复盘。顶层命名空间固定：

```json
{
  "filters": {
    "liquidity_filter": {
      "passed": true,
      "avg_amount_5d": 150000000.0,
      "min_amount_threshold": 50000000.0
    },
    "st_filter": { "passed": true }
  },
  "strategy": {
    "name": "breakout_v1",
    "params": { "lookback": 20, "breakout_ratio": 0.03 },
    "raw_outputs": { "highest_high": 15.6, "current_close": 16.1 }
  },
  "risk": {
    "volatility_check": { "is_extreme": false, "val": 0.08 }
  }
}
```

## 6. tracks YAML 契约
配置文件存放于 `pulse-core/pulse_core/screener/tracks/` 目录下。

**示例：scalp.yaml（超短赛道）**
```yaml
track: scalp
description: "超短赛道：打板与强势股二次突破"
top_n: 10
filters:
  - limit_up_only
  - hot_sector
strategies:
  - second_wave_breakout
  - limit_up_board_hit
```

**示例：swing.yaml（波段赛道）**
```yaml
track: swing
description: "波段赛道：中线上行趋势中的缩量回踩"
top_n: 20
filters:
  - liquidity_base
  - ma20_upward
strategies:
  - volume_shrink_rebound
```

## 7. Strategy 契约（Protocol）

### 7.1 接口签名
Strategy 必须实现以下接口。推荐在 `score()` 内部进行维度校验。

```python
class Strategy(Protocol):
    name: str  # 必须与文件名（不含 .py）一致

    def score(self, ctx: PickContext) -> Scorecard | None:
        """
        根据上下文打分。
        不符合入选条件则返回 None。
        """
        ...
```

**顶层 score 派生**：daily_picks 表的 `score` 列由 Scorecard 各维度按 weight 加权求和得出，等同 `Scorecard.final_score()`。Strategy 不直接写顶层 score；runner 在落库前从 Scorecard 派生。

### 7.2 不入选语义
返回 `None` 意味着该股票甚至不应出现在候选列表的末尾。Strategy 拥有最终否决权。

### 7.3 风险维度强制规则
Scorecard 必须包含至少 1 个 `kind="risk"` 的维度。Runner 在 Strategy 产出后立即调用 `Scorecard.validate()` 校验：缺失 risk 维度或 weight 总和 ≠ 1.0（容差 1e-6）即抛 `ValueError`，整个赛道执行失败（不容错、不过滤）。

## 8. Filter 契约（Protocol）

### 8.1 接口签名
Filter 侧重于 DataFrame 的行列剪裁。

ScreenerData 是 runner 持有的容器，封装 daily / basic / trend / momentum / volume / moneyflow 当日切片。

```python
class Filter(Protocol):
    name: str  # 必须与文件名（不含 .py）一致

    def apply(self, data: ScreenerData) -> pd.DataFrame:
        """
        从 ScreenerData（6 张源表的当日切片容器）筛选候选 DataFrame。
        返回的 DataFrame 必须包含 ts_code 列，并附加 _filter_{name} 详情列。
        """
        ...
```

### 8.2 输出约定
Filter 输出 DataFrame 必须包含 `ts_code` 列；同时附加一列 `_filter_{name}`（其中 `{name}` = 该 Filter 的 name 属性）记录关键中间值（如阈值、实际值、布尔结果）。Runner 末尾会把所有 `_filter_*` 列打包写入 signals.filters。

## 9. Runner 流程

**执行步骤详情**：
1. **环境准备**：从配置加载 `tracks/*.yaml`。
2. **全局加载**：调用 `ingestion` 模块接口获取当日基础行情与指标的全量 DataFrame。
3. **第一层漏斗**：执行各赛道共用的通用 Filter。
4. **赛道循环**：针对每个 Track：
    - **第二层漏斗**：执行赛道专属 Filter（如行业准入、特定形态初筛）。
    - **第三层漏斗**：对剩余股票，迭代调用该赛道下的所有 Strategy。
    - **验证**：检查 Strategy 产出的 Scorecard 是否符合 weight 总和 = 1.0 且含有风险维度。
    - **排序与截取**：按 score 降序排列，取前 `top_n` 名。
5. **持久化**：单一事务原子写入 `daily_picks` 及衍生表（virtual_positions / notifications_outbox 等）。事务边界与原子性规则详见 architecture.md §5.3。

**Python-like 伪代码**：
```python
def screener_main(trade_date):
    # 1. 加载数据 (圈 1 & 2)
    master_df = load_all_market_data(trade_date)
    
    # 2. 遍历赛道
    for track in load_tracks():
        # Layer 1 & 2: 批量过滤
        candidate_df = master_df.copy()
        for f in track.filters:
            candidate_df = f.apply(candidate_df)
            
        # Layer 3: 打分
        picks = []
        for _, row in candidate_df.iterrows():
            ctx = PickContext(row)
            for strategy in track.strategies:
                card = strategy.score(ctx)
                if card and validate_card(card):
                    picks.append({"ts_code": row.ts_code, "score": card.final_score(), "scorecard": card})
        
        # 结果截取与入库
        final_picks = sorted(picks, key=lambda p: p["score"], reverse=True)[:track.top_n]
        db.save_picks_atomic(final_picks, track)  # 同事务写入 daily_picks 及衍生表
```

## 10. 红线（禁止）
- ❌ Strategy 返回 Scorecard 但不含 `kind="risk"` 的维度
- ❌ Scorecard weight 总和不等于 1.0（容差 1e-6）
- ❌ 绕过 `screener/runner.py` 直写 `daily_picks`（破坏 architecture.md §5.3 同事务原子性）
- ❌ Filter 在结果为空时崩溃（必须空 DataFrame 优雅传递到下游）
- ❌ `scorecard.dimensions` / `signals` 的 JSONB 内部使用 `camelCase`（DB / Python 层必须 `snake_case`）

## 11. 新增 checklist

### 新策略
- [ ] 在 `pulse_core/screener/strategies/` 创建 `{key}.py`
- [ ] 实现 Strategy Protocol（定义 `name: str = "{key}"` + `score(ctx) -> Scorecard | None`）
- [ ] Scorecard 至少含 1 个 `kind="risk"` 维度
- [ ] Scorecard weight 总和严格 = 1.0
- [ ] 在某个 `tracks/{track}.yaml` 的 `strategies` 列表注册
- [ ] `pulse-web/src/lib/strategy-meta.ts` 增加元数据
- [ ] `pulse-core/tests/screener/strategies/test_{key}.py` 单元测试

### 新过滤器
- [ ] 在 `pulse_core/screener/filters/` 创建 `{key}.py`
- [ ] 实现 Filter Protocol（定义 `name: str = "{key}"` + `apply(data) -> pd.DataFrame`）
- [ ] 输出 DataFrame 含 `ts_code` 列与 `_filter_{key}` 详情列
- [ ] 在某个 `tracks/{track}.yaml` 的 `filters` 列表注册
- [ ] `pulse-core/tests/screener/filters/test_{key}.py` 单元测试

### 新赛道
- [ ] 在 `pulse_core/screener/tracks/` 创建 `{track}.yaml`
- [ ] 定义 `track` / `description` / `top_n` 字段
- [ ] `filters` 列表至少 1 项（已注册的 Filter）
- [ ] `strategies` 列表至少 1 项（已注册的 Strategy）
- [ ] `pulse-web/src/lib/track-meta.ts` 增加元数据

## 12. 延迟决策（TBD）
- `v_picks_resonance` 视图：等多策略落地再加
- 二级索引：等 pulse-api 路由查询模式定型再加
- 风险维度 v2：财务暴雷 / 大股东减持（需新增 ingestion）
- 风险维度 v3：用户黑名单（需用户配置系统）
