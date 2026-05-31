"""Date parsing utilities for Tushare-format date strings."""

from datetime import date, datetime
from typing import Any

import pandas as pd


def parse_date(s: Any) -> date | None:
    """Parse Tushare-format date string '20260520' -> date(2026, 5, 20).

    Returns None for NaN, empty, or unparseable values.
    """
    if pd.isna(s) or not s:
        return None
    try:
        return datetime.strptime(str(s), "%Y%m%d").date()
    except (ValueError, TypeError):
        return None
