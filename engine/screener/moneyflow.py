from datetime import date

import pandas as pd

from compute.indicators import load_with_indicators
from lib.db import acquire
from screener.base import Pick, Screener

LOOKBACK_DAYS = 3  # 连续性判定回看（含今天）
MAIN_NET_RATIO_MIN = 0.03  # 硬过滤：主力净流入占当日总成交额最低门槛
CONTINUITY_REQUIRED_DAYS = 2  # 3 天内至少 2 天净流入（硬过滤）
ELG_DOMINANT_RATIO = 0.5  # 特大单净流入占主力净流入 ≥ 50% 视为机构主导


class MoneyflowScreener(Screener):
    name = "moneyflow"

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
        flow_df = await self._load_moneyflow(ts_code, trade_date)
        if len(flow_df) < 1:
            return None

        flow_df = flow_df.sort_values("trade_date").reset_index(drop=True)
        today_flow = flow_df.iloc[-1]
        if today_flow["trade_date"] != trade_date:
            return None

        price_df = await load_with_indicators(ts_code, trade_date)
        if len(price_df) < 1:
            return None
        today_price = price_df.iloc[-1]
        if pd.isna(today_price["amount"]) or today_price["amount"] <= 0:
            return None

        total_amt = float(today_price["amount"])

        main_net_today = self._main_net(today_flow)
        if main_net_today is None or main_net_today <= 0:
            return None

        main_net_ratio = main_net_today / total_amt
        if main_net_ratio < MAIN_NET_RATIO_MIN:
            return None

        positive_days = 0
        for _, row in flow_df.iloc[-LOOKBACK_DAYS:].iterrows():
            net = self._main_net(row)
            if net is not None and net > 0:
                positive_days += 1
        if positive_days < CONTINUITY_REQUIRED_DAYS:
            return None

        elg_net = self._elg_net(today_flow)
        elg_ratio = (elg_net / main_net_today) if elg_net is not None else None

        vol_ratio = today_price.get("vol_ratio_5")
        if pd.isna(vol_ratio):
            vol_ratio = None
        else:
            vol_ratio = float(vol_ratio)

        score, reasons = self._score(main_net_ratio, positive_days, vol_ratio, elg_ratio)
        if score < 50:
            return None

        signals = {
            "main_net": float(main_net_today),
            "main_net_ratio": float(main_net_ratio),
            "total_amount": total_amt,
            "positive_days_3d": positive_days,
            "elg_net": float(elg_net) if elg_net is not None else None,
            "elg_ratio": float(elg_ratio) if elg_ratio is not None else None,
            "vol_ratio_5": vol_ratio,
            "reasons": reasons,
        }
        return Pick(ts_code=ts_code, score=score, signals=signals)

    async def _load_moneyflow(self, ts_code: str, trade_date: date) -> pd.DataFrame:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT trade_date,
                       buy_lg_amount, sell_lg_amount,
                       buy_elg_amount, sell_elg_amount
                FROM moneyflow_cn
                WHERE ts_code = $1 AND trade_date <= $2
                ORDER BY trade_date DESC
                LIMIT $3
                """,
                ts_code,
                trade_date,
                LOOKBACK_DAYS,
            )
        return pd.DataFrame([dict(r) for r in rows])

    @staticmethod
    def _main_net(row) -> float | None:
        cols = ["buy_lg_amount", "sell_lg_amount", "buy_elg_amount", "sell_elg_amount"]
        if any(pd.isna(row[c]) for c in cols):
            return None
        return (row["buy_lg_amount"] + row["buy_elg_amount"]) - (
            row["sell_lg_amount"] + row["sell_elg_amount"]
        )

    @staticmethod
    def _elg_net(row) -> float | None:
        if pd.isna(row["buy_elg_amount"]) or pd.isna(row["sell_elg_amount"]):
            return None
        return row["buy_elg_amount"] - row["sell_elg_amount"]

    def _score(
        self,
        main_net_ratio: float,
        positive_days: int,
        vol_ratio: float | None,
        elg_ratio: float | None,
    ) -> tuple[float, list[dict]]:
        score = 30.0
        reasons = [{"text": "主力净流入", "score": 30, "max": 30, "dim": "trigger"}]

        if main_net_ratio >= 0.10:
            score += 30
            reasons.append({"text": "极强净流入", "score": 30, "max": 30, "dim": "net_ratio"})
        elif main_net_ratio >= 0.05:
            score += 20
            reasons.append({"text": "强净流入", "score": 20, "max": 30, "dim": "net_ratio"})
        else:
            score += 10
            reasons.append({"text": "净流入", "score": 10, "max": 30, "dim": "net_ratio"})

        if positive_days >= 3:
            score += 20
            reasons.append({"text": "三连净流入", "score": 20, "max": 20, "dim": "continuity"})
        elif positive_days >= 2:
            score += 10
            reasons.append({"text": "两日净流入", "score": 10, "max": 20, "dim": "continuity"})

        if vol_ratio is not None and vol_ratio >= 1.0:
            score += 10
            reasons.append({"text": "放量配合", "score": 10, "max": 10, "dim": "volume_match"})

        if elg_ratio is not None and elg_ratio >= ELG_DOMINANT_RATIO:
            score += 10
            reasons.append(
                {"text": "机构主导", "score": 10, "max": 10, "dim": "elg_dominant"}
            )

        return score, reasons
