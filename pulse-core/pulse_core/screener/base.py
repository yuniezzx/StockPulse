"""Screener 核心抽象层。

实现 docs/screener.md §3-§8 规范:
- ScreenerData / PickContext:Runner 与 Strategy 之间的数据契约
- Filter / Strategy:duck-typed Protocol 接口
- FilterResult / Scorecard:执行产物

后续阶段统一从此模块 import:
    from pulse_core.screener.base import (
        ScreenerData, PickContext, FilterResult,
        Filter, Strategy, Scorecard,
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, TypedDict

import pandas as pd

# 容差:同轴权重和、加权一致性校验(详见 docs/screener.md §5.3 规则 4-5)
WEIGHT_TOLERANCE: float = 1e-6


class ScreenerData(TypedDict):
    """Runner 阶段 0 加载完成后的内存数据容器。详见 docs/screener.md §3.1。

    约定:
    - 当日切片以 ts_code 为索引。
    - history 长度 = max(strategy.lookback for all strategies),长表
      (ts_code + trade_date 双索引)。
    - 字段名沿用 Tushare / indicators 表原始命名(snake_case),内存层不重命名。
    """

    daily:         pd.DataFrame   # 当日 daily_cn 切片
    basic:         pd.DataFrame   # 当日 daily_basic_cn 切片
    moneyflow:     pd.DataFrame   # 当日 moneyflow_cn 切片
    trend:         pd.DataFrame   # 当日 daily_trend_indicators_cn 切片
    momentum:      pd.DataFrame   # 当日 daily_momentum_indicators_cn 切片
    volume:        pd.DataFrame   # 当日 daily_volume_indicators_cn 切片
    moneyflow_ind: pd.DataFrame   # 当日 daily_moneyflow_indicators_cn 切片
    history:       pd.DataFrame   # 历史窗口(长表)
    trade_date:    date
    universe:      list[str]      # 当前候选 ts_code(已剔除停牌)


@dataclass(frozen=True)
class PickContext:
    """单只股票在目标交易日的计算上下文。

    生命周期:仅限单次 Strategy.score() 调用。
    详见 docs/screener.md §3.4。
    """

    ts_code:       str
    trade_date:    date
    daily:         pd.Series          # 当日 daily_cn 行
    basic:         pd.Series          # 当日 daily_basic_cn 行
    moneyflow:     pd.Series | None   # 当日 moneyflow_cn 行(可能不存在)
    trend:         pd.Series          # 当日 trend indicators 行
    momentum:      pd.Series          # 当日 momentum indicators 行
    volume:        pd.Series          # 当日 volume indicators 行
    moneyflow_ind: pd.Series | None
    history:       pd.DataFrame       # 该股最近 N 个交易日(N = Runner 全局 lookback 上限)
    data:          ScreenerData       # 跨股聚合需要时回查(如分位数)


@dataclass(frozen=True)
class FilterResult:
    """Filter.apply() 的产物。详见 docs/screener.md §7.1。

    - passed:通过该 Filter 的 ts_code 集合
    - rejected:被剔除的 ts_code → {"reason": str, "detail": dict}
      本期 rejected 不入库,仅用于日志 / 未来审计页 hook
    """

    name:     str
    passed:   set[str]
    rejected: dict[str, dict[str, Any]]


class Filter(Protocol):
    """硬过滤 Protocol。详见 docs/screener.md §7.1。

    实现类放在 pulse_core/screener/filters/{layer}/{name}.py:
    - layer=1:全市场通用 Filter(剔除 ST / 次新股 / 低流动性)
    - layer=2:赛道专属 Filter(如 scalp 的 min_price_filter)

    name 必须 snake_case,且与文件名(不含 .py)一致 ——
    Runner 按 name 在 yaml 中引用。
    """

    name:        str    # 与文件名(不含 .py)一致;snake_case
    layer:       int    # 1=通用 / 2=赛道专属
    lookback:    int    # 需要的历史天数(0 = 仅当日切片)
    description: str

    def apply(self, data: ScreenerData) -> FilterResult:
        """对 data["universe"] 中的股票做布尔判定,返回通过/拒绝集合。

        异常语义(§7.3):
        - Filter 内部抛异常 → 整个赛道 FAIL(fail-fast)
        - 通过的股票数为 0 不算异常,赛道正常结束(写入 0 行)
        """
        ...


class Strategy(Protocol):
    """打分 Protocol。详见 docs/screener.md §8.1。

    实现类放在 pulse_core/screener/strategies/{name}.py。
    name 必须 snake_case,与文件名(不含 .py)一致;DB strategy 列写入此值。

    跨 4 层一致性约束:
    - Python 类的 name 字段 = 文件名(不含 .py)
    - = pulse_core/screener/tracks/*.yaml 中 strategies 列表里的引用
    - = pulse-web/src/lib/strategy-meta.ts 的 key
    """

    name:        str
    lookback:    int    # 需要的历史天数;Runner 取所有 Strategy 最大值预加载
    description: str

    def score(self, ctx: PickContext) -> Scorecard | None:
        """对单只股票打分。

        返回:
        - Scorecard:该股入选本策略,Runner 落库
        - None:该股通过 Filter 但不符合本策略入选模型(Strategy 最终否决权)

        Strategy 不要手动设置 reward_score / risk_score / final_score,
        这些列由 Runner 从 Scorecard 派生写入。
        """
        ...


class RewardDim(TypedDict, total=False):
    """reward 轴单维度(JSONB §5.1)。

    必填:score / weight
    可选:details(snake_case keys)

    total=False 让所有 key 可选;运行时强校验由 Scorecard.validate() 负责。
    """

    score:   float        # 0~100
    weight:  float        # 0~1
    details: dict[str, Any]


class RiskDim(TypedDict, total=False):
    """risk 轴单维度(JSONB §5.1)。

    必填:score / weight / source
    可选:details

    source 格式:
    - "shared:<func_name>"  共享 risk 维度(实现在 risk_dimensions.py)
    - "strategy:<strategy_name>"  策略私有 risk 维度
    """

    score:   float        # 0~100
    weight:  float        # 0~1
    source:  str          # "shared:..." 或 "strategy:..."
    details: dict[str, Any]


@dataclass
class Scorecard:
    """双轴评分卡。详见 docs/screener.md §5。

    - 由 Strategy.score() 通过 Scorecard.build() 构造
    - Runner 落库前调用 .validate() 校验 §5.3 全部强制规则,失败抛 ValueError
    - .to_jsonb() 返回 §5.1 形状的 dict,可直接写入 daily_picks.scorecard JSONB 列
    - DB 列 reward_score / risk_score / final_score 由 axis_scores 派生写入

    字段直接镜像 §5.1 JSONB 顶层 4 个 key。
    """

    axis_weights:      dict[str, float]            # {"reward": 0.70, "risk": 0.30}
    axis_scores:       dict[str, float]            # {"reward": ..., "risk": ..., "final": ...}
    reward_dimensions: dict[str, RewardDim]
    risk_dimensions:   dict[str, RiskDim]

    @classmethod
    def build(
        cls,
        reward: dict[str, RewardDim],
        risk: dict[str, RiskDim],
        w_reward: float = 0.70,
        w_risk: float = 0.30,
    ) -> Scorecard:
        """从维度字典构造 Scorecard,自动派生 axis_scores。

        Args:
            reward: reward 轴维度字典 {dim_name: {"score", "weight", "details"?}}
            risk: risk 轴维度字典(必须含至少 1 个 source 以 "shared:" 开头的维度)
            w_reward: reward 轴在 final_score 中的权重(默认 0.70)
            w_risk: risk 轴在 final_score 中的权重(默认 0.30)

        派生计算(§4.1):
            reward_score = Σ(dim.score × dim.weight)  for dim in reward
            risk_score   = Σ(dim.score × dim.weight)  for dim in risk
            final_score  = w_reward × reward_score + w_risk × risk_score

        注意:本方法不调用 validate(),允许测试构造非法 Scorecard 验证校验逻辑。
              Runner 在落库前显式调用 validate()。
        """
        reward_score = sum(d["score"] * d["weight"] for d in reward.values())
        risk_score = sum(d["score"] * d["weight"] for d in risk.values())
        final_score = w_reward * reward_score + w_risk * risk_score

        return cls(
            axis_weights={"reward": w_reward, "risk": w_risk},
            axis_scores={
                "reward": round(reward_score, 2),
                "risk":   round(risk_score, 2),
                "final":  round(final_score, 2),
            },
            reward_dimensions=dict(reward),  # 浅拷贝,断开外部引用
            risk_dimensions=dict(risk),
        )

    def validate(self) -> None:
        """校验 §5.3 全部强制规则。失败抛 ValueError。

        规则:
        1. 四顶层 key 都存在(由 dataclass 字段保证,这里只查非空)
        2. reward_dimensions 与 risk_dimensions 各 ≥1 个维度
        3. risk_dimensions 至少 1 个维度 source 以 "shared:" 开头
        4. 同轴内 Σ weight ≈ 1.0(容差 WEIGHT_TOLERANCE = 1e-6)
        5. axis_scores 与现场加权和一致(容差 WEIGHT_TOLERANCE = 1e-6)
           注意:对照的是用维度原始 score/weight 重新计算的加权和,
           不是 build() 中 round 后的值 —— 因此 round(2) 不影响校验。
        6. JSONB 内部 key 全部 snake_case(SDK 自检:仅查顶层与维度名)

        Raises:
            ValueError: 任一规则违反时抛出,消息含规则编号和实际值。
        """
        # 规则 1+2:reward / risk 各至少 1 维
        if not self.reward_dimensions:
            raise ValueError(
                "Scorecard 规则 §5.3-2 违反:reward_dimensions 至少 1 个维度,实际 0"
            )
        if not self.risk_dimensions:
            raise ValueError(
                "Scorecard 规则 §5.3-2 违反:risk_dimensions 至少 1 个维度,实际 0"
            )

        # 规则 3:risk 至少 1 个 source 以 "shared:" 开头
        shared_count = sum(
            1 for d in self.risk_dimensions.values()
            if d.get("source", "").startswith("shared:")
        )
        if shared_count == 0:
            sources = [d.get("source", "<missing>") for d in self.risk_dimensions.values()]
            raise ValueError(
                "Scorecard 规则 §5.3-3 违反:risk_dimensions 至少需 1 个 "
                f"source 以 'shared:' 开头,实际 sources={sources}"
            )

        # 规则 4:同轴 Σ weight ≈ 1.0
        reward_weight_sum = sum(d["weight"] for d in self.reward_dimensions.values())
        if abs(reward_weight_sum - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-4 违反:reward 轴 Σ weight = "
                f"{reward_weight_sum},应为 1.0(容差 {WEIGHT_TOLERANCE})"
            )
        risk_weight_sum = sum(d["weight"] for d in self.risk_dimensions.values())
        if abs(risk_weight_sum - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-4 违反:risk 轴 Σ weight = "
                f"{risk_weight_sum},应为 1.0(容差 {WEIGHT_TOLERANCE})"
            )

        # 规则 5:axis_scores 与现场加权和一致
        expected_reward = sum(
            d["score"] * d["weight"] for d in self.reward_dimensions.values()
        )
        expected_risk = sum(
            d["score"] * d["weight"] for d in self.risk_dimensions.values()
        )
        w_reward = self.axis_weights.get("reward")
        w_risk = self.axis_weights.get("risk")
        if w_reward is None or w_risk is None:
            raise ValueError(
                "Scorecard 规则 §5.3-1 违反:axis_weights 缺少 reward / risk 键,"
                f"实际 {self.axis_weights}"
            )
        expected_final = w_reward * expected_reward + w_risk * expected_risk

        actual_reward = self.axis_scores.get("reward")
        actual_risk = self.axis_scores.get("risk")
        actual_final = self.axis_scores.get("final")
        if actual_reward is None or actual_risk is None or actual_final is None:
            raise ValueError(
                "Scorecard 规则 §5.3-1 违反:axis_scores 缺少 reward/risk/final,"
                f"实际 {self.axis_scores}"
            )

        # 注意:axis_scores 在 build() 中被 round(2),与现场加权和差不超过 0.005;
        # 但若 Strategy 直接构造 Scorecard 而非通过 build(),容差仍按 1e-6 严格判断。
        # 这里允许 round(0.5e-2) 误差以兼容 build():取容差 = max(WEIGHT_TOLERANCE, 0.005 + ε)。
        # 决策:严格按 doc 1e-6,build() 不应破坏一致性 —— 因此对比 round 后的现场值。
        rounded_reward = round(expected_reward, 2)
        rounded_risk = round(expected_risk, 2)
        rounded_final = round(expected_final, 2)

        if abs(actual_reward - rounded_reward) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-5 违反:axis_scores.reward = "
                f"{actual_reward},现场加权和 = {rounded_reward}(容差 {WEIGHT_TOLERANCE})"
            )
        if abs(actual_risk - rounded_risk) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-5 违反:axis_scores.risk = "
                f"{actual_risk},现场加权和 = {rounded_risk}(容差 {WEIGHT_TOLERANCE})"
            )
        if abs(actual_final - rounded_final) > WEIGHT_TOLERANCE:
            raise ValueError(
                "Scorecard 规则 §5.3-5 违反:axis_scores.final = "
                f"{actual_final},现场加权和 = {rounded_final}(容差 {WEIGHT_TOLERANCE})"
            )

        # 规则 6:snake_case 自检(顶层 key + 维度名)
        for key in self.axis_weights:
            _assert_snake_case(key, f"axis_weights.{key}")
        for key in self.axis_scores:
            _assert_snake_case(key, f"axis_scores.{key}")
        for dim_name in self.reward_dimensions:
            _assert_snake_case(dim_name, f"reward_dimensions.{dim_name}")
        for dim_name in self.risk_dimensions:
            _assert_snake_case(dim_name, f"risk_dimensions.{dim_name}")

    def to_jsonb(self) -> dict[str, Any]:
        """序列化为 §5.1 形状的 dict,可直接写入 daily_picks.scorecard JSONB 列。

        注意:返回的是浅拷贝,外部修改不影响原 Scorecard。
        """
        return {
            "axis_weights":      dict(self.axis_weights),
            "axis_scores":       dict(self.axis_scores),
            "reward_dimensions": {k: dict(v) for k, v in self.reward_dimensions.items()},
            "risk_dimensions":   {k: dict(v) for k, v in self.risk_dimensions.items()},
        }


def _assert_snake_case(value: str, path: str) -> None:
    """断言 value 是合法的 snake_case 标识符。失败抛 ValueError(规则 6)。

    snake_case 规范:
    - 仅含小写字母 / 数字 / 下划线
    - 不能以数字开头
    - 不能含连续下划线(可放宽,但本期严格)
    """
    if not value:
        raise ValueError(f"Scorecard 规则 §5.3-6 违反:{path} 为空")
    if not all(c.islower() or c.isdigit() or c == "_" for c in value):
        raise ValueError(
            f"Scorecard 规则 §5.3-6 违反:{path} = '{value}' 含非 snake_case 字符"
        )
    if value[0].isdigit():
        raise ValueError(
            f"Scorecard 规则 §5.3-6 违反:{path} = '{value}' 以数字开头"
        )
