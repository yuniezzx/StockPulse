from datetime import date

import pandas as pd

from compute.indicators import load_with_indicators
from lib.db import acquire
from screener.base import Pick, Screener


class MACDCrossScreener(Screener):
    name = "macd_cross"

    async def run(self, trade_date: date) -> list[Pick]:
        universe = await self._get_universe()
        picks = []
        for ts_code in universe:
            pick = await self._evaluate(ts_code, trade_date)
            if pick:
                picks.append(pick)
        return picks

    async def _get_universe(self) -> list[str]:
        async with acquire() as conn:
            rows = await conn.fetch("SELECT ts_code FROM stocks_cn WHERE list_status = 'L'")
        return [r["ts_code"] for r in rows]

    async def _evaluate(self, ts_code: str, trade_date: date) -> Pick | None:
        df = await load_with_indicators(ts_code, trade_date)
        if len(df) < 2:
            return None

        yesterday = df.iloc[-2]
        today = df.iloc[-1]

        # 数据完整性检查
        required = ["dif", "dea", "hist", "ma20", "ma60", "vol_ratio_5", "close_qfq"]
        if any(pd.isna(today[c]) for c in required):
            return None
        if any(pd.isna(yesterday[c]) for c in ["dif", "dea"]):
            return None

        # 触发判断
        if not (yesterday["dif"] <= yesterday["dea"] and today["dif"] > today["dea"]):
            return None

        # 零轴上硬性必要条件：深水金叉（dif <= 0）胜率低，整体过滤
        if today["dif"] <= 0:
            return None

        # 打分
        score, reasons = self._score(today)
        if score < 30:  # 阈值过滤
            return None

        signals = {
            "dif": float(today["dif"]),
            "dea": float(today["dea"]),
            "hist": float(today["hist"]),
            "close": float(today["close_qfq"]),
            "ma20": float(today["ma20"]),
            "ma60": float(today["ma60"]),
            "vol_ratio_5": float(today["vol_ratio_5"]),
            "reasons": reasons,
        }
        return Pick(ts_code=ts_code, score=score, signals=signals)

    def _score(self, today) -> tuple[float, list[dict]]:
        score = 0.0
        reasons = []

        if today["dif"] > 0:
            score += 40
            reasons.append({"text": "零轴上金叉", "score": 40, "max": 40, "dim": "zero_axis"})

        if today["close_qfq"] > today["ma20"]:
            score += 15
            reasons.append({"text": "站上 MA20", "score": 15, "max": 15, "dim": "trend"})

        if today["close_qfq"] > today["ma60"]:
            score += 15
            reasons.append({"text": "站上 MA60", "score": 15, "max": 15, "dim": "trend"})

        if today["vol_ratio_5"] >= 1.5:
            score += 20
            reasons.append({"text": "放量金叉", "score": 20, "max": 20, "dim": "volume"})

        if today["hist"] > 0:
            score += 10
            reasons.append({"text": "HIST 强势", "score": 10, "max": 10, "dim": "histogram"})

        return score, reasons
