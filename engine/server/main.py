from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from loguru import logger

from lib.db import acquire, close_pool, get_pool


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
