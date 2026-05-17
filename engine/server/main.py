from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date as Date

from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel

from lib.db import acquire, close_pool, get_pool


class PickItem(BaseModel):
    ts_code: str
    name: str | None
    strategy: str
    score: float
    signals: dict


class PickTodayResponse(BaseModel):
    trade_date: Date | None
    total: int
    picks: list[PickItem]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("server starting: initializing db pool")
    await get_pool()
    yield
    logger.info("server stopping: closing db pool")
    await close_pool()


app = FastAPI(title="StockPulse Engine API", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz/db")
async def healthz_db() -> dict[str, object]:
    try:
        async with acquire() as conn:
            await conn.fetchval("SELECT 1")
            count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                """
            )
        return {"db": "ok", "tables": count}
    except Exception as e:
        logger.exception("db healthcheck failed")
        raise HTTPException(status_code=503, detail=f"db unavailable: {e}") from e


@app.get("/picks/today", response_model=PickTodayResponse)
async def picks_today() -> PickTodayResponse:
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT MAX(trade_date) AS d FROM daily_picks
            )
            SELECT p.trade_date, p.ts_code, s.name, p.strategy,
                   p.score, p.signals
            FROM daily_picks p
            LEFT JOIN stocks_cn s ON p.ts_code = s.ts_code
            WHERE p.trade_date = (SELECT d FROM latest)
            ORDER BY p.strategy, p.score DESC
            """
        )

    if not rows:
        return PickTodayResponse(trade_date=None, total=0, picks=[])

    return PickTodayResponse(
        trade_date=rows[0]["trade_date"],
        total=len(rows),
        picks=[
            PickItem(
                ts_code=r["ts_code"],
                name=r["name"],
                strategy=r["strategy"],
                score=r["score"],
                signals=r["signals"],
            )
            for r in rows
        ],
    )
