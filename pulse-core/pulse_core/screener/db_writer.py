"""Stage 4:原子写入 daily_picks + daily_pick_candidates。

每条赛道一个事务,同时写两张表:
- daily_picks: top_n 截断后的决策结果(下游业务流消费)
- daily_pick_candidates: 全量打分结果含 rank(调试 / 共振分析 / 复盘)

幂等 —— 同日重跑同时覆盖两张表。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import asyncpg

from pulse_core.lib.logger import logger
from pulse_core.screener.scorecard import Scorecard


@dataclass(frozen=True, slots=True)
class PickRow:
    """一行待写入数据。Runner 装配,db_writer 落库。

    rank: 该 strategy 在该赛道 + 交易日内按 final_score DESC 的排名(1 起)。
    """

    ts_code:   str
    strategy:  str
    scorecard: Scorecard
    rank:      int = 0


@dataclass(frozen=True, slots=True)
class TrackWriteResult:
    """一条赛道的写入结果。"""

    picks_inserted:      int
    candidates_inserted: int


async def write_track_picks(
    conn: asyncpg.Connection,
    trade_date: date,
    track: str,
    top_picks: list[PickRow],
    all_candidates: list[PickRow],
) -> TrackWriteResult:
    """原子写一条赛道的 picks + candidates。

    流程(单事务):
        1. DELETE FROM daily_picks            WHERE trade_date=$1 AND track=$2
        2. DELETE FROM daily_pick_candidates  WHERE trade_date=$1 AND track=$2
        3. INSERT top_picks       → daily_picks
        4. INSERT all_candidates  → daily_pick_candidates
        (任一空集合只 DELETE,实现"空赛道 = 清空旧数据"幂等)

    Args:
        top_picks:      已排序截断到 top_n 的 picks(rank 字段被忽略)。
        all_candidates: 全量打分结果,rank 已由 runner 赋值(1 起)。

    Raises:
        ValueError: 任一 Scorecard.validate() 失败 —— 整条赛道回滚。
    """
    for p in top_picks:
        p.scorecard.validate()
    for p in all_candidates:
        p.scorecard.validate()

    async with conn.transaction():
        await conn.execute(
            "DELETE FROM daily_picks WHERE trade_date = $1 AND track = $2",
            trade_date, track,
        )
        await conn.execute(
            "DELETE FROM daily_pick_candidates WHERE trade_date = $1 AND track = $2",
            trade_date, track,
        )

        picks_rows = [_pick_to_row(p, trade_date, track) for p in top_picks]
        if picks_rows:
            await conn.executemany(_INSERT_PICKS_SQL, picks_rows)

        cand_rows = [_candidate_to_row(p, trade_date, track) for p in all_candidates]
        if cand_rows:
            await conn.executemany(_INSERT_CANDIDATES_SQL, cand_rows)

    logger.info(
        f"write_track_picks: track={track} trade_date={trade_date} "
        f"picks={len(picks_rows)} candidates={len(cand_rows)}"
    )
    return TrackWriteResult(
        picks_inserted=len(picks_rows),
        candidates_inserted=len(cand_rows),
    )


_INSERT_PICKS_SQL = """
INSERT INTO daily_picks (
    trade_date, track, strategy, ts_code,
    reward_score, risk_score, final_score,
    w_reward, w_risk,
    scorecard
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
"""


_INSERT_CANDIDATES_SQL = """
INSERT INTO daily_pick_candidates (
    trade_date, track, strategy, ts_code, rank,
    reward_score, risk_score, final_score,
    w_reward, w_risk,
    scorecard
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
"""


def _pick_to_row(p: PickRow, trade_date: date, track: str) -> tuple[object, ...]:
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


def _candidate_to_row(p: PickRow, trade_date: date, track: str) -> tuple[object, ...]:
    sc = p.scorecard
    return (
        trade_date,
        track,
        p.strategy,
        p.ts_code,
        p.rank,
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
