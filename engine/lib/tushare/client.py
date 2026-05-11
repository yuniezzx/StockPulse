"""Tushare Pro client wrapper: SDK initialization + retry policy."""

from typing import Any

import requests
import tushare as ts
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from lib.config import settings

_pro = None

_TOKEN_LENGTH = 56


def _require_token() -> str:
    token = settings.TUSHARE_TOKEN

    if len(token) != _TOKEN_LENGTH:
        raise RuntimeError(f"Tushare token must be {_TOKEN_LENGTH} chars; got {len(token)}")

    return token


def get_pro_client() -> Any:
    """Return a singleton Tushare Pro client, lazily initialized."""

    global _pro

    if _pro is None:
        token = _require_token()
        ts.set_token(token)
        _pro = ts.pro_api()
        # Set SDK endpoint to our proxy, which handles auth and caching.
        _pro._DataApi__http_url = settings.TUSHARE_API_URL
        logger.info(f"Tushare client initialized: {settings.TUSHARE_API_URL}")

    return _pro


tushare_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, IOError)),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        f"Tushare request failed (attempt {rs.attempt_number}), retrying..."
    ),
)
