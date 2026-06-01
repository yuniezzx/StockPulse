"""涨停复盘策略 —— scalp 赛道首发。

业务模型(详见 docs/screener.md §11.4):
    强势股二次启动 —— 近 10 日有过涨停且当日未涨停,处于回踩 / 整理阶段。

入选条件(否则 score() 返回 None):
    1. 最近 LOOKBACK 日内至少 1 次 pct_chg >= LIMIT_UP_PCT
    2. 当日 pct_chg < LIMIT_UP_PCT(防追高)

打分:
    Reward 轴 3 维:
        - recent_limit_up_strength (0.4):近 10 日涨停次数 / LOOKBACK × 100
        - volume_expansion         (0.3):当日 vol / vol_ma5,截到 0~100
        - pullback_quality         (0.3):涨停后回踩深度,理想 -3% ~ -8%(高斯峰)

    Risk 轴 1 维:
        - liquidity_risk           (1.0):shared:liquidity_risk
"""

from __future__ import annotations

import math

import pandas as pd

from pulse_core.screener.base import PickContext, RewardDim, Scorecard
from pulse_core.screener.risk_dimensions import compute_liquidity_risk

LOOKBACK: int = 10
LIMIT_UP_PCT: float = 9.5
PULLBACK_PEAK_PCT: float = -5.5
PULLBACK_SIGMA: float = 2.5


class LimitUpReplayStrategy:
    name = "limit_up_replay"
    lookback = LOOKBACK
    description = "涨停复盘:近 10 日有过涨停 + 当日未涨停 + 回踩到位"

    def score(self, ctx: PickContext) -> Scorecard | None:
        if ctx.history.empty:
            return None

        recent = ctx.history.tail(LOOKBACK)
        if "pct_chg" not in recent.columns:
            return None

        limit_up_days = int((recent["pct_chg"] >= LIMIT_UP_PCT).sum())
        if limit_up_days == 0:
            return None

        today_pct = ctx.daily.get("pct_chg")
        if today_pct is None or pd.isna(today_pct):
            return None
        if float(today_pct) >= LIMIT_UP_PCT:
            return None

        reward = self._compute_reward(ctx, recent, limit_up_days)
        risk = {"liquidity_risk": compute_liquidity_risk(ctx)}
        return Scorecard.build(reward=reward, risk=risk)

    @staticmethod
    def _compute_reward(
        ctx: PickContext,
        recent: pd.DataFrame,
        limit_up_days: int,
    ) -> dict[str, RewardDim]:
        strength_score = round(min(100.0, limit_up_days / LOOKBACK * 100.0), 2)

        today_vol = float(ctx.daily.get("vol") or 0.0)
        vol_ma5 = float(recent["vol"].tail(5).mean()) if "vol" in recent.columns else 0.0
        if vol_ma5 > 0:
            ratio = today_vol / vol_ma5
            volume_score = round(min(100.0, ratio * 50.0), 2)
        else:
            volume_score = 0.0

        last_limit_up_idx = recent.index[recent["pct_chg"] >= LIMIT_UP_PCT][-1]
        last_limit_up_close = float(recent.loc[last_limit_up_idx, "close"])
        today_close = float(ctx.daily["close"])
        pullback_pct = (today_close - last_limit_up_close) / last_limit_up_close * 100.0
        pullback_score = _gaussian_score(
            value=pullback_pct,
            peak=PULLBACK_PEAK_PCT,
            sigma=PULLBACK_SIGMA,
        )

        return {
            "recent_limit_up_strength": {
                "score":   strength_score,
                "weight":  0.4,
                "details": {"limit_up_days": limit_up_days, "lookback": LOOKBACK},
            },
            "volume_expansion": {
                "score":   volume_score,
                "weight":  0.3,
                "details": {"today_vol": today_vol, "vol_ma5": round(vol_ma5, 2)},
            },
            "pullback_quality": {
                "score":   pullback_score,
                "weight":  0.3,
                "details": {
                    "pullback_pct":         round(pullback_pct, 2),
                    "last_limit_up_close":  last_limit_up_close,
                    "today_close":          today_close,
                },
            },
        }


def _gaussian_score(value: float, peak: float, sigma: float) -> float:
    """高斯峰打分:value 越接近 peak 越高,远离衰减。返回 0~100,2 位小数。

    f(x) = 100 * exp(-((x - peak) / sigma) ** 2 / 2)
    """
    score = 100.0 * math.exp(-(((value - peak) / sigma) ** 2) / 2)
    return round(max(0.0, min(100.0, score)), 2)
