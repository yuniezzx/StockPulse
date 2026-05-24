"""合成 OHLCV + adj_factor 测试数据生成器。

设计原则：
- 完全确定性（无 random），同样的输入永远产出同样的输出，便于 golden value 比对
- 60 行 = 足够覆盖 ma60 / ema26 + 几天验证段
- 单只股 ts_code="000001.SZ"，简化测试（多股串扰由专项测试覆盖）
- adj_factor 前 30 行 = 1.0，后 30 行 = 1.5，模拟 1.5x 拆股（用于 T3 apply_qfq 验证）
"""

from __future__ import annotations

import math

import pandas as pd

TS_CODE = "000001.SZ"
N_ROWS = 60
START_DATE = "2024-01-02"


def synthetic_ohlcv() -> pd.DataFrame:
    """返回 60 行确定性 OHLCV DataFrame。

    列：ts_code, trade_date, open, high, low, close, vol, amount, pre_close
    所有数值列为 float / int，trade_date 为 pd.Timestamp。
    """
    dates = pd.bdate_range(start=START_DATE, periods=N_ROWS)

    close = [10.0 + i * 0.1 + math.sin(i / 3.0) * 0.5 for i in range(N_ROWS)]
    pre_close = [close[0]] + close[:-1]
    open_ = pre_close.copy()
    high = [max(o, c) * 1.01 for o, c in zip(open_, close, strict=True)]
    low = [min(o, c) * 0.99 for o, c in zip(open_, close, strict=True)]
    vol = [10000 + i * 100 + (i % 7) * 500 for i in range(N_ROWS)]
    amount = [v * c * 100 for v, c in zip(vol, close, strict=True)]

    df = pd.DataFrame(
        {
            "ts_code": TS_CODE,
            "trade_date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "vol": vol,
            "amount": amount,
            "pre_close": pre_close,
        }
    )
    return df


def synthetic_adj_factor() -> pd.DataFrame:
    """返回 60 行 adj_factor DataFrame，模拟 1.5x 拆股。

    前 30 行 adj_factor = 1.0，后 30 行 adj_factor = 1.5。
    trade_date 与 synthetic_ohlcv 对齐。
    """
    dates = pd.bdate_range(start=START_DATE, periods=N_ROWS)
    adj = [1.0] * 30 + [1.5] * 30

    df = pd.DataFrame(
        {
            "ts_code": TS_CODE,
            "trade_date": dates,
            "adj_factor": adj,
        }
    )
    return df
