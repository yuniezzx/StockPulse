"""Numeric conversion utilities for Tushare DataFrame fields.

Tushare 返回的 DataFrame 用 pandas NaN 表示缺失值。写 DB 时需转 None；
某些价格字段需按复权因子缩放。
"""

from typing import Any

import pandas as pd


def to_float(v: Any) -> float | None:
    """Convert value to float, mapping pandas NaN to None."""
    if pd.isna(v):
        return None
    return float(v)


def scale(v: float | None, factor: float) -> float | None:
    """Multiply v by factor, preserving None."""
    return v * factor if v is not None else None
