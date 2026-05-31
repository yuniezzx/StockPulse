"""Loguru initialization.

Single source of logger configuration. Import `logger` from here, or directly
from `loguru` — both reference the same global instance (loguru is a singleton).

Format (D3 light customization):
    HH:mm:ss | LEVEL | module:function:line - message
    e.g.  18:30:05 | INFO  | pulse_core.ingestion.daily_cn:sync_daily_cn:67 - ...
"""

import sys

from loguru import logger

from pulse_core.lib.config import settings

_LOG_FORMAT = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <5}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def _configure() -> None:
    """Replace loguru's default handler with our customized one."""
    logger.remove()
    logger.add(
        sys.stderr,
        format=_LOG_FORMAT,
        level=settings.CORE_LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=False,  # do not leak variable values in tracebacks (prod-friendly)
    )


_configure()

__all__ = ["logger"]
