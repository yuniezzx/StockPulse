"""真 DB 端到端测试。

默认 skip,设置环境变量 PULSE_INTEGRATION=1 才跑:
    PULSE_INTEGRATION=1 uv run pytest tests/screener/test_e2e_real_db.py -v

前提:
    - 本地 PostgreSQL 已 migrate 到最新
    - daily_cn / daily_basic_cn / stocks_cn 等源表已同步真实数据
    - .env 中 DATABASE_URL 配置正确

测试流程:
    1. 选最近一个 daily_cn 有数据的交易日
    2. 跑 run_screener(只跑 scalp 赛道)
    3. 断言 daily_picks 至少有 1 行
    4. cleanup:删自己写的行
"""

from __future__ import annotations

import os
from datetime import date

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("PULSE_INTEGRATION") != "1",
    reason="设置 PULSE_INTEGRATION=1 才跑真 DB e2e 测试",
)


@pytest.mark.asyncio
async def test_scalp_track_e2e_real_db():
    from pulse_core.lib.db import acquire, close_pool
    from pulse_core.screener.runner import run_screener

    try:
        async with acquire() as conn:
            row = await conn.fetchrow(
                "SELECT MAX(trade_date) AS d FROM daily_cn"
            )
            assert row and row["d"], "daily_cn 无数据,先跑 ingestion"
            trade_date: date = row["d"]

        result = await run_screener(trade_date, tracks=["scalp"])

        assert result.status in ("success", "partial"), (
            f"Runner 失败:{result.to_details()}"
        )
        scalp_result = next(tr for tr in result.track_results if tr.track == "scalp")
        assert scalp_result.status == "success", (
            f"scalp 赛道失败:{scalp_result.error}"
        )

        async with acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM daily_picks "
                "WHERE trade_date = $1 AND track = 'scalp' AND strategy = 'limit_up_replay'",
                trade_date,
            )
            assert count == scalp_result.inserted, (
                f"DB 写入数 {count} 与 Runner 报告 {scalp_result.inserted} 不符"
            )

            cand_count = await conn.fetchval(
                "SELECT COUNT(*) FROM daily_pick_candidates "
                "WHERE trade_date = $1 AND track = 'scalp' AND strategy = 'limit_up_replay'",
                trade_date,
            )
            assert cand_count >= count, (
                f"candidates 行数 {cand_count} 应 ≥ picks 行数 {count}"
            )
            max_rank = await conn.fetchval(
                "SELECT MAX(rank) FROM daily_pick_candidates "
                "WHERE trade_date = $1 AND track = 'scalp'",
                trade_date,
            )
            assert max_rank == cand_count, (
                f"rank 应连续:max={max_rank} vs count={cand_count}"
            )

            await conn.execute(
                "DELETE FROM daily_picks WHERE trade_date = $1 AND track = 'scalp'",
                trade_date,
            )
            await conn.execute(
                "DELETE FROM daily_pick_candidates WHERE trade_date = $1 AND track = 'scalp'",
                trade_date,
            )
    finally:
        await close_pool()
