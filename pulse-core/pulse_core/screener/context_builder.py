from __future__ import annotations

import pandas as pd

from pulse_core.screener.contracts import PickContext, ScreenerData


def _build_context(ts_code: str, data: ScreenerData) -> PickContext:
    """从 ScreenerData 切片出单股 PickContext。"""
    history = data["history"]
    if ts_code in history.index.get_level_values("ts_code"):
        stock_history = history.xs(ts_code, level="ts_code")
    else:
        stock_history = pd.DataFrame()

    return PickContext(
        ts_code=ts_code,
        trade_date=data["trade_date"],
        daily=data["daily"].loc[ts_code],
        basic=data["basic"].loc[ts_code] if ts_code in data["basic"].index else None,
        moneyflow=data["moneyflow"].loc[ts_code] if ts_code in data["moneyflow"].index else None,
        trend=data["trend"].loc[ts_code] if ts_code in data["trend"].index else None,
        momentum=data["momentum"].loc[ts_code] if ts_code in data["momentum"].index else None,
        volume=data["volume"].loc[ts_code] if ts_code in data["volume"].index else None,
        moneyflow_ind=(
            data["moneyflow_ind"].loc[ts_code]
            if ts_code in data["moneyflow_ind"].index
            else None
        ),
        history=stock_history,
        data=data,
    )
