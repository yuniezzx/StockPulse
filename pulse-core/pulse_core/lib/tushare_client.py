"""Tushare Pro client wrapper: singleton + endpoint override + smart retry.

私有 tushare 代理：endpoint 注入到 tushare SDK 内部字段
（依赖 SDK 实现细节，升级 tushare 后需验证 _DataApi__http_url 是否仍存在）。
"""

from functools import cache
from typing import Any

import requests
import tushare as ts
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from pulse_core.lib.config import settings

_TOKEN_PLACEHOLDER = "your_tushare_token_here"
_MIN_TOKEN_LENGTH = 32


def _validate_token(token: str) -> str:
    if not token or token == _TOKEN_PLACEHOLDER:
        raise RuntimeError("TUSHARE_TOKEN not set in .env (still placeholder or empty)")
    if len(token) < _MIN_TOKEN_LENGTH:
        logger.warning(f"Tushare token unusually short ({len(token)} chars)")
    return token


@cache
def get_pro_client() -> Any:
    """Return a singleton Tushare Pro client, lazily initialized.

    Endpoint is overridden to point at the private proxy (settings.TUSHARE_API_URL)
    via the SDK's internal `_DataApi__http_url` attribute. This is name-mangled
    private API; re-verify after upgrading tushare.
    """
    token = _validate_token(settings.TUSHARE_TOKEN)
    ts.set_token(token)
    pro = ts.pro_api()
    pro._DataApi__http_url = settings.TUSHARE_API_URL  # noqa: SLF001
    logger.info(f"Tushare client ready: endpoint={settings.TUSHARE_API_URL}")
    return pro


# --- retry policy ---
# 重试场景：
#   1. 网络异常（连接超时、读超时、连接失败）
#   2. 限流错误（私有代理或 tushare 官方返回的速率限制类提示）
# 不重试：
#   - 权限/参数等业务错误（重试也没用，浪费配额）
_RATE_LIMIT_KEYWORDS = ("rate limit", "请求过于频繁", "频率超限", "timeout")


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, requests.Timeout | requests.ConnectionError | OSError):
        return True
    msg = str(exc).lower()
    return any(k in msg for k in _RATE_LIMIT_KEYWORDS)


def _log_retry(retry_state: Any) -> None:
    exc = retry_state.outcome.exception()
    logger.warning(
        f"Tushare retry: attempt={retry_state.attempt_number}, exc={type(exc).__name__}: {exc}"
    )


tushare_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_should_retry),
    reraise=True,
    before_sleep=_log_retry,
)
