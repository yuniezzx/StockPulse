from datetime import date

import pandas as pd

from compute.indicators import load_with_indicators
from lib.db import acquire
from screener.base import Pick, Screener

BREAKOUT_WINDOW = 60  # 突破判定窗口（前 N 个交易日）
BREAKOUT_BUFFER = 1.005  # 突破缓冲：今日 close 要 > 前高 * 1.005 才算真突破


class BreakoutScreener(Screener):
    name = "breakout"

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
                  AND list_date <= $1::date - INTERVAL '180 days'
                """,
                trade_date,
            )
        return [r["ts_code"] for r in rows]

    async def _evaluate(self, ts_code: str, trade_date: date) -> Pick | None:
        df = await load_with_indicators(ts_code, trade_date)
        if len(df) < BREAKOUT_WINDOW + 2:
            return None

        today = df.iloc[-1]
        yesterday = df.iloc[-2]

        required = ["close_qfq", "high_qfq", "low_qfq", "vol_ratio_5", "ma60"]
        if any(pd.isna(today[c]) for c in required):
            return None
        if pd.isna(yesterday["close_qfq"]):
            return None

        prev_high_60 = df["close_qfq"].iloc[-(BREAKOUT_WINDOW + 1) : -1].max()
        if pd.isna(prev_high_60):
            return None

        if today["close_qfq"] <= prev_high_60 * BREAKOUT_BUFFER:
            return None

        # 硬过滤 2: 昨日未突破（确保是"突破当日"，非连续创新高）
        if yesterday["close_qfq"] > prev_high_60:
            return None

        score, reasons = self._score(today, prev_high_60)
        if score < 50:
            return None

        signals = {
            "close": float(today["close_qfq"]),
            "prev_high_60": float(prev_high_60),
            "breakout_pct": float((today["close_qfq"] - prev_high_60) / prev_high_60),
            "vol_ratio_5": float(today["vol_ratio_5"]),
            "ma60": float(today["ma60"]),
            "high": float(today["high_qfq"]),
            "low": float(today["low_qfq"]),
            "reasons": reasons,
        }
        return Pick(ts_code=ts_code, score=score, signals=signals)

    def _score(self, today, prev_high_60: float) -> tuple[float, list[dict]]:
        score = 30.0
        reasons = [{"text": "突破 60 日新高", "score": 30, "max": 30, "dim": "trigger"}]

        vol_ratio = today["vol_ratio_5"]
        if vol_ratio >= 1.5:
            score += 30
            reasons.append({"text": "放量突破", "score": 30, "max": 30, "dim": "volume"})
        elif vol_ratio >= 1.0:
            score += 15
            reasons.append({"text": "温和放量", "score": 15, "max": 30, "dim": "volume"})

        breakout_pct = (today["close_qfq"] - prev_high_60) / prev_high_60
        if breakout_pct >= 0.03:
            score += 20
            reasons.append({"text": "强力突破", "score": 20, "max": 20, "dim": "strength"})
        elif breakout_pct >= 0.01:
            score += 10
            reasons.append({"text": "有效突破", "score": 10, "max": 20, "dim": "strength"})

        if today["close_qfq"] > today["ma60"]:
            score += 10
            reasons.append({"text": "趋势向上", "score": 10, "max": 10, "dim": "trend"})

        range_ = today["high_qfq"] - today["low_qfq"]
        if range_ > 0:
            pos = (today["close_qfq"] - today["low_qfq"]) / range_
            if pos >= 0.7:
                score += 10
                reasons.append(
                    {"text": "收盘强势", "score": 10, "max": 10, "dim": "close_position"}
                )

        return score, reasons
