"""PostgreSQL connection pool (asyncpg).

Single source of DB access for pulse-core. Use `acquire()` as an async context
manager to get a connection from the shared pool.

JSONB / JSON columns are encoded/decoded as Python dicts automatically.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from pulse_core.lib.config import settings
from pulse_core.lib.logger import logger

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register JSON/JSONB codecs for every new connection in the pool."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def get_pool() -> asyncpg.Pool:
    """Return the singleton pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=1,
            max_size=4,
            command_timeout=30,
            init=_init_connection,
        )
        # Mask credentials in log: print only the database tail of the DSN.
        dsn_tail = settings.DATABASE_URL.rsplit("@", 1)[-1]
        logger.info(f"DB pool initialized: {dsn_tail} (min=1, max=4)")
    return _pool


async def close_pool() -> None:
    """Close the pool. Safe to call multiple times."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def acquire() -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection from the pool as an async context manager."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def _healthcheck() -> None:
    """Connect, run SELECT 1, print server version. Useful for ops verification."""
    try:
        async with acquire() as conn:
            one = await conn.fetchval("SELECT 1")
            version = await conn.fetchval("SHOW server_version")
            logger.info(f"DB healthcheck OK: SELECT 1 -> {one}, server_version={version}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_healthcheck())
