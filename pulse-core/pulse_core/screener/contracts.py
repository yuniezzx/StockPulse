"""Screener 核心契约层。

实现 docs/screener.md §3-§8 规范:
- ScreenerData / PickContext: Runner 与 Strategy 之间的数据契约
- Filter / Strategy: duck-typed Protocol 接口
- FilterResult: 执行产物
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any, Protocol, TypedDict

import pandas as pd

if TYPE_CHECKING:
    from pulse_core.screener.scorecard import Scorecard


class ScreenerData(TypedDict):
    """Runner 阶段 0 加载完成后的内存数据容器。详见 docs/screener.md §3.1。

    约定:
    - 当日切片以 ts_code 为索引。
    - history 长度 = max(strategy.lookback for all strategies),长表
      (ts_code + trade_date 双索引)。
    - 字段名沿用 Tushare / indicators 表原始命名(snake_case),内存层不重命名。
    """

    daily: pd.DataFrame
    basic: pd.DataFrame
    moneyflow: pd.DataFrame
    trend: pd.DataFrame
    momentum: pd.DataFrame
    volume: pd.DataFrame
    moneyflow_ind: pd.DataFrame
    history: pd.DataFrame
    stocks: pd.DataFrame
    trade_date: date
    universe: list[str]


@dataclass(frozen=True)
class PickContext:
    """单只股票在目标交易日的计算上下文。

    生命周期: 仅限单次 Strategy.score() 调用。
    详见 docs/screener.md §3.4。
    """

    ts_code: str
    trade_date: date
    daily: pd.Series
    basic: pd.Series | None
    moneyflow: pd.Series | None
    trend: pd.Series | None
    momentum: pd.Series | None
    volume: pd.Series | None
    moneyflow_ind: pd.Series | None
    history: pd.DataFrame
    data: ScreenerData


@dataclass(frozen=True)
class FilterResult:
    """Filter.apply() 的产物。详见 docs/screener.md §7.1。

    - passed: 通过该 Filter 的 ts_code 集合
    - rejected: 被剔除的 ts_code → {"reason": str, "detail": dict}
      本期 rejected 不入库,仅用于日志 / 未来审计页 hook
    """

    name: str
    passed: set[str]
    rejected: dict[str, dict[str, Any]]


class Filter(Protocol):
    """硬过滤 Protocol。详见 docs/screener.md §7.1。

    实现类放在 pulse_core/screener/filters/universal/{name}.py（layer 1）
    或 pulse_core/screener/filters/track/{name}.py（layer 2）。

    name 必须 snake_case,且与文件名(不含 .py)一致 ——
    Runner 按 name 在 yaml 中引用。
    """

    name: str
    layer: int
    lookback: int
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

    name: str
    lookback: int
    description: str

    def score(self, ctx: PickContext) -> Scorecard | None:
        """对单只股票打分。

        返回:
        - Scorecard: 该股入选本策略,Runner 落库
        - None: 该股通过 Filter 但不符合本策略入选模型(Strategy 最终否决权)

        Strategy 不要手动设置 reward_score / risk_score / final_score,
        这些列由 Runner 从 Scorecard 派生写入。
        """
        ...
