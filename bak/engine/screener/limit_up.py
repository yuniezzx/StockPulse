from datetime import date

import pandas as pd

from lib.db import acquire
from screener.base import Pick, Screener

LOOKBACK_DAYS = 60
FIRST_LIMIT_UP_WINDOW = 10  # 前 N 个交易日内没涨停才算"首板"
PRICE_TOLERANCE = 0.01  # 涨停判定容忍浮点误差（元）


class LimitUpScreener(Screener):
    name = "limit_up"

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
                  AND list_date <= $1::date - INTERVAL '60 days'
                """,
                trade_date,
            )
        return [r["ts_code"] for r in rows]

    async def _evaluate(self, ts_code: str, trade_date: date) -> Pick | None:
        df = await self._load_history(ts_code, trade_date)
        if len(df) < 1:
            return None

        today = df.iloc[0]
        if pd.isna(today["up_limit"]) or pd.isna(today["close"]) or pd.isna(today["vol"]):
            return None

        # 硬过滤 1: 今日涨停
        if today["close"] < today["up_limit"] - PRICE_TOLERANCE:
            return None

        # 硬过滤 2: 前 N 个交易日内未涨停（有几天查几天）
        prev = df.iloc[1 : 1 + FIRST_LIMIT_UP_WINDOW]
        if len(prev) > 0:
            prev_valid = prev.dropna(subset=["close", "up_limit"])
            if (prev_valid["close"] >= prev_valid["up_limit"] - PRICE_TOLERANCE).any():
                return None

        # 打分
        score, reasons = self._score(df)
        if score < 40:
            return None

        signals = {
            "close": float(today["close"]),
            "up_limit": float(today["up_limit"]),
            "vol": float(today["vol"]),
            "high_60d": float(df["close"].max()),
            "vol_ratio_5": self._calc_vol_ratio(df),
            "reasons": reasons,
        }
        return Pick(ts_code=ts_code, score=score, signals=signals)

    async def _load_history(self, ts_code: str, trade_date: date) -> pd.DataFrame:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT d.trade_date, d.close, d.vol, l.up_limit
                FROM daily_cn d
                LEFT JOIN stk_limit_cn l USING (ts_code, trade_date)
                WHERE d.ts_code = $1
                  AND d.trade_date <= $2
                ORDER BY d.trade_date DESC
                LIMIT $3
                """,
                ts_code,
                trade_date,
                LOOKBACK_DAYS,
            )
        return pd.DataFrame([dict(r) for r in rows])

    def _calc_vol_ratio(self, df: pd.DataFrame) -> float | None:
        prev_5 = df.iloc[1:6]["vol"].dropna()
        if len(prev_5) == 0:
            return None
        avg = prev_5.mean()
        if avg == 0:
            return None
        return float(df.iloc[0]["vol"] / avg)

    def _score(self, df: pd.DataFrame) -> tuple[float, list[dict]]:
        today = df.iloc[0]
        score = 40.0
        reasons = [{"text": "首次涨停", "score": 40, "max": 40, "dim": "trigger"}]

        high_60 = df["close"].max()
        position = today["close"] / high_60 if high_60 > 0 else 1.0
        if position <= 0.7:
            score += 30
            reasons.append({"text": "低位首板", "score": 30, "max": 30, "dim": "position"})
        elif position <= 0.85:
            score += 15
            reasons.append({"text": "中位首板", "score": 15, "max": 30, "dim": "position"})

        vol_ratio = self._calc_vol_ratio(df)
        if vol_ratio is not None:
            if 1.0 <= vol_ratio <= 3.0:
                score += 20
                reasons.append({"text": "温和放量", "score": 20, "max": 20, "dim": "volume"})
            elif vol_ratio > 3.0:
                score += 10
                reasons.append({"text": "巨量涨停", "score": 10, "max": 20, "dim": "volume"})

        if today["close"] <= 30:
            score += 10
            reasons.append({"text": "低价小盘", "score": 10, "max": 10, "dim": "price"})

        return score, reasons
