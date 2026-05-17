from datetime import date

import pandas as pd

from compute.indicators import load_with_indicators
from lib.db import acquire
from screener.base import Pick, Screener

TREND_LOOKBACK = 30  # 趋势判定回看窗口
TREND_MIN_GAIN = 0.05  # 30 日累计涨幅最低要求（5%）
TREND_STRONG_GAIN = 0.15  # 强势趋势线（15%）
NEAR_MA20_RATIO = 1.03  # close 在 MA20 上方 3% 内视为"接近"
PULLBACK_DEPTH_MIN = 0.05  # 健康回调最小深度（5%）
PULLBACK_DEPTH_MAX = 0.15  # 健康回调最大深度（15%，超过则趋势可能转弱）
VOL_SHRINK_THRESHOLD = 0.8  # 缩量阈值
VOL_NORMAL_THRESHOLD = 1.2  # 正常量能上限


class PullbackScreener(Screener):
    name = "pullback"

    async def run(self, trade_date: date) -> list[Pick]:
        universe = await self._get_universe(trade_date)
        picks = []
        for ts_code in universe:
            pick = await self._evaluate(ts_code, trade_date)
            if pick:
                picks.append(pick)
        return picks

    async def _get_universe(self, trade_date: date) -> list[str]:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ts_code
                FROM stocks_cn
                WHERE list_status = 'L'
                  AND name NOT LIKE '%ST%'
                  AND list_date <= $1::date - INTERVAL '90 days'
                """,
                trade_date,
            )
        return [r["ts_code"] for r in rows]

    async def _evaluate(self, ts_code: str, trade_date: date) -> Pick | None:
        df = await load_with_indicators(ts_code, trade_date)
        if len(df) < TREND_LOOKBACK + 1:
            return None

        today = df.iloc[-1]
        required = ["close_qfq", "open_qfq", "low_qfq", "ma20", "ma60", "vol_ratio_5"]
        if any(pd.isna(today[c]) for c in required):
            return None

        if today["close_qfq"] <= today["ma60"]:
            return None

        # 必须先涨过，才有回调可言
        trend_start = df.iloc[-(TREND_LOOKBACK + 1)]
        if pd.isna(trend_start["close_qfq"]):
            return None
        trend_gain = (today["close_qfq"] - trend_start["close_qfq"]) / trend_start["close_qfq"]
        if trend_gain < TREND_MIN_GAIN:
            return None

        touched_ma20 = today["low_qfq"] <= today["ma20"]
        near_ma20 = today["close_qfq"] <= today["ma20"] * NEAR_MA20_RATIO
        if not (touched_ma20 or near_ma20):
            return None

        window_high = df.iloc[-(TREND_LOOKBACK + 1) :]["close_qfq"].max()
        pullback_depth = (
            (window_high - today["close_qfq"]) / window_high if window_high > 0 else 0
        )

        score, reasons = self._score(today, touched_ma20, trend_gain, pullback_depth)
        if score < 50:
            return None

        signals = {
            "close": float(today["close_qfq"]),
            "open": float(today["open_qfq"]),
            "low": float(today["low_qfq"]),
            "ma20": float(today["ma20"]),
            "ma60": float(today["ma60"]),
            "trend_gain_30d": float(trend_gain),
            "pullback_depth": float(pullback_depth),
            "vol_ratio_5": float(today["vol_ratio_5"]),
            "touched_ma20": bool(touched_ma20),
            "reasons": reasons,
        }
        return Pick(ts_code=ts_code, score=score, signals=signals)

    def _score(
        self, today, touched_ma20: bool, trend_gain: float, pullback_depth: float
    ) -> tuple[float, list[dict]]:
        score = 30.0
        reasons = [{"text": "趋势回踩 MA20", "score": 30, "max": 30, "dim": "trigger"}]

        if touched_ma20:
            score += 20
            reasons.append({"text": "盘中触及 MA20", "score": 20, "max": 20, "dim": "touch"})
        else:
            score += 10
            reasons.append({"text": "接近 MA20", "score": 10, "max": 20, "dim": "touch"})

        vol_ratio = today["vol_ratio_5"]
        if vol_ratio <= VOL_SHRINK_THRESHOLD:
            score += 20
            reasons.append({"text": "缩量回踩", "score": 20, "max": 20, "dim": "volume"})
        elif vol_ratio <= VOL_NORMAL_THRESHOLD:
            score += 10
            reasons.append({"text": "量能平稳", "score": 10, "max": 20, "dim": "volume"})

        # 阳线收回（开盘后回踩、收盘拉回）
        if today["close_qfq"] > today["open_qfq"]:
            score += 10
            reasons.append({"text": "阳线收回", "score": 10, "max": 10, "dim": "candle"})

        if trend_gain >= TREND_STRONG_GAIN:
            score += 10
            reasons.append(
                {"text": "强势趋势", "score": 10, "max": 10, "dim": "trend_strength"}
            )

        if PULLBACK_DEPTH_MIN <= pullback_depth <= PULLBACK_DEPTH_MAX:
            score += 10
            reasons.append(
                {"text": "健康回调幅度", "score": 10, "max": 10, "dim": "pullback_depth"}
            )

        return score, reasons
