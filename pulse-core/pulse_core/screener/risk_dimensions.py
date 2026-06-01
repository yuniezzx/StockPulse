"""共享 risk 维度库。

每个函数返回 RiskDim 字典,可被任意 Strategy 调用并组装到 Scorecard。
source 字段统一为 "shared:<func_name>",符合 docs/screener.md §5.4 规范。
"""

from __future__ import annotations

import math

from pulse_core.screener.base import PickContext, RiskDim


def compute_liquidity_risk(ctx: PickContext) -> RiskDim:
    """流动性风险维度。基于 daily_basic_cn.amount 横截面分位数。

    详见 docs/screener.md §5.4。

    算法:
        amount_rank_pct = 该股 amount 在当日 universe 全体中的百分位排名(0~1)
        score = round(amount_rank_pct × 100, 2)  # 越高越流动性好,越安全

    返回的 weight 默认 1.0(占位);Strategy 在 Scorecard.build() 时按需覆盖。

    Raises:
        ValueError: 该股 amount 缺失或 NaN(应该在 low_liquidity_filter 阶段已剔除)。
    """
    amount = ctx.basic.get("amount")
    if amount is None or (isinstance(amount, float) and math.isnan(amount)):
        raise ValueError(
            f"compute_liquidity_risk: {ctx.ts_code} 的 amount 为空/NaN,"
            "应在 Layer 1 low_liquidity_filter 阶段已剔除"
        )

    all_amount = ctx.data["basic"]["amount"]
    rank_pct = float(all_amount.rank(pct=True).loc[ctx.ts_code])
    score = round(rank_pct * 100, 2)

    return {
        "score":   score,
        "weight":  1.0,
        "source":  "shared:liquidity_risk",
        "details": {
            "amount":          float(amount),
            "amount_rank_pct": round(rank_pct, 4),
        },
    }
