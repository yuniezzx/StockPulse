from __future__ import annotations

from typing import cast

import pandas as pd

from pulse_core.screener.contracts import PickContext
from pulse_core.screener.scorecard import RewardDim


def compute_volume_expansion(ctx: PickContext, recent: pd.DataFrame, *, weight: float) -> RewardDim:
    """当日量能放大维度：today_vol / vol_ma5，截到 0~100。可被任意 Strategy 复用。"""
    today_vol = float(ctx.daily.get("vol") or 0.0)
    vol_series = cast(pd.Series, recent["vol"]) if "vol" in recent.columns else None
    vol_ma5 = float(vol_series.tail(5).mean()) if vol_series is not None else 0.0
    score = round(min(100.0, today_vol / vol_ma5 * 50.0), 2) if vol_ma5 > 0 else 0.0
    return {
        "score": score,
        "weight": weight,
        "details": {"today_vol": today_vol, "vol_ma5": round(vol_ma5, 2)},
    }
