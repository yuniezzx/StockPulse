"""Filter / Strategy 注册表(name → 类对象的映射)。

设计:字典写死(YAGNI)。新增 filter / strategy 时显式 import 并加进字典。
yaml 中按 name 引用 → Runner 调 get_filter / get_strategy 解析为类。

Phase 3 仅注册 Layer 1 universal filter;Phase 4 加 Layer 2 + strategy。
"""

from __future__ import annotations

from pulse_core.screener.contracts import Filter, Strategy
from pulse_core.screener.filters.track.min_price_filter import MinPriceFilter
from pulse_core.screener.filters.track.recent_active_filter import RecentActiveFilter
from pulse_core.screener.filters.universal.low_liquidity_filter import LowLiquidityFilter
from pulse_core.screener.filters.universal.new_stock_filter import NewStockFilter
from pulse_core.screener.filters.universal.st_filter import STFilter
from pulse_core.screener.strategies.limit_up_replay import LimitUpReplayStrategy

# Layer 1 通用 Filter:Runner 硬编码顺序执行,不在 yaml 中声明
UNIVERSAL_FILTERS: tuple[type[Filter], ...] = (
    STFilter,
    NewStockFilter,
    LowLiquidityFilter,
)

# Layer 2 赛道专属 Filter:yaml 中按 name 引用
_TRACK_FILTERS: dict[str, type[Filter]] = {
    "min_price_filter":     MinPriceFilter,
    "recent_active_filter": RecentActiveFilter,
}

# Strategy 注册表:yaml 中按 name 引用
_STRATEGIES: dict[str, type[Strategy]] = {
    "limit_up_replay": LimitUpReplayStrategy,
}


def get_filter(name: str) -> type[Filter]:
    """按 name 获取 Layer 2 Filter 类。未注册抛 KeyError。"""
    if name not in _TRACK_FILTERS:
        available = sorted(_TRACK_FILTERS.keys())
        raise KeyError(
            f"Filter '{name}' 未注册。已注册 Layer 2 filters: {available}。"
            "请在 pulse_core/screener/registry.py 中显式 import + 注册。"
        )
    return _TRACK_FILTERS[name]


def get_strategy(name: str) -> type[Strategy]:
    """按 name 获取 Strategy 类。未注册抛 KeyError。"""
    if name not in _STRATEGIES:
        available = sorted(_STRATEGIES.keys())
        raise KeyError(
            f"Strategy '{name}' 未注册。已注册 strategies: {available}。"
            "请在 pulse_core/screener/registry.py 中显式 import + 注册。"
        )
    return _STRATEGIES[name]
