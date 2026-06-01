"""Stage 4:原子写入 daily_picks。

每条赛道一个事务:DELETE 旧行 + INSERT 新行。幂等 —— 同日重跑覆盖。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import asyncpg

from pulse_core.lib.logger import logger
from pulse_core.screener.base import Scorecard


@dataclass(frozen=True, slots=True)
class PickRow:
    """一行 daily_picks 待写入数据。Runner 装配,db_writer 落库。"""

    ts_code:   str
    strategy:  str
    scorecard: Scorecard


async def write_track_picks(
    conn: asyncpg.Connection,
    trade_date: date,
    track: str,
    picks: list[PickRow],
) -> int:
    """原子写一条赛道的全部 picks。

    流程(单事务):
        1. DELETE FROM daily_picks WHERE trade_date=$1 AND track=$2
        2. INSERT 新 picks(若 picks 为空,只 DELETE,实现"空赛道 = 清空旧数据"幂等)

    Returns:
        实际 INSERT 的行数。

    Raises:
        ValueError: 任一 Scorecard.validate() 失败 —— 整条赛道回滚。
    """
    for p in picks:
        p.scorecard.validate()

    async with conn.transaction():
        delete_result = await conn.execute(
            "DELETE FROM daily_picks WHERE trade_date = $1 AND track = $2",
            trade_date, track,
        )
        deleted = _parse_rowcount(delete_result)

        if not picks:
            logger.info(
                f"write_track_picks: track={track} trade_date={trade_date} "
                f"deleted={deleted} inserted=0 (empty track)"
            )
            return 0

        rows = [_pick_to_row(p, trade_date, track) for p in picks]
        await conn.executemany(_INSERT_SQL, rows)

    logger.info(
        f"write_track_picks: track={track} trade_date={trade_date} "
        f"deleted={deleted} inserted={len(rows)}"
    )
    return len(rows)


_INSERT_SQL = """
INSERT INTO daily_picks (
    trade_date, track, strategy, ts_code,
    reward_score, risk_score, final_score,
    w_reward, w_risk,
    scorecard
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
"""


def _pick_to_row(p: PickRow, trade_date: date, track: str) -> tuple:
    sc = p.scorecard
    return (
        trade_date,
        track,
        p.strategy,
        p.ts_code,
        sc.axis_scores["reward"],
        sc.axis_scores["risk"],
        sc.axis_scores["final"],
        sc.axis_weights["reward"],
        sc.axis_weights["risk"],
        sc.to_jsonb(),
    )


def _parse_rowcount(command_tag: str) -> int:
    """从 asyncpg command tag 'DELETE 5' 提取行数。"""
    _, _, n = command_tag.rpartition(" ")
    try:
        return int(n)
    except ValueError:
        return 0
