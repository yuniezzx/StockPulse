"""
技术指标层：基于前复权价格计算短中线选股常用指标。

指标说明：
    MA5/10/20/60: 简单移动平均线（5/10/20/60 日）。
        用途：判断趋势方向。短期均线在长期均线之上 = 多头排列；交叉 = 趋势转折信号。

    MACD (DIF/DEA/HIST): 指数平滑异同移动平均线（参数 12/26/9）。
        DIF  = EMA12 - EMA26，快线，反映短期动量。
        DEA  = DIF 的 9 日 EMA，慢线，平滑后的趋势线。
        HIST = (DIF - DEA) * 2，柱状图，反映动量加速/减速。
        用途：DIF 上穿 DEA = 金叉（买入信号）；HIST 由负转正 = 动量启动。

    RSI14: 相对强弱指数（14 日，Wilder 平滑）。
        范围 0-100。> 70 超买，< 30 超卖，50 为多空分界。
        用途：判断短期超买超卖；背离信号（价格新高 RSI 不新高 = 顶背离）。

    ATR14: 平均真实波幅（14 日）。
        反映绝对波动幅度（元/股）。
        用途：止损位计算（如 close - 2*ATR）、仓位管理（波动大则仓位小）。

    vol_ma5: 成交量 5 日均值。
    vol_ratio_5: 当日成交量 / vol_ma5，即量比。
        用途：> 1.5 放量，< 0.5 缩量；放量突破比缩量突破更可靠。

注意：
    - 所有价格类指标基于 close_qfq/high_qfq/low_qfq（前复权价），保证跨除权事件连续。
    - vol 不复权（送股会使 vol 不可比），但 vol_ratio_5 是相对值不受影响。
    - 长窗口指标（ma60、MACD warmup 33 天）在数据初期为 NaN，调用方需自行 dropna。
"""

from datetime import date

import pandas as pd
import pandas_ta_classic as ta

from compute.adjust import to_qfq
from lib.db import acquire

LOOKBACK_DAYS = 120


async def load_daily(ts_code: str, end_date: date, days: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """加载最近 N 个交易日的日线数据，按 trade_date 升序。"""
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT d.trade_date, d.open, d.high, d.low, d.close, d.vol, d.amount, a.adj_factor
            FROM daily_cn d
            JOIN adj_factor_cn a USING (ts_code, trade_date)
            WHERE d.ts_code = $1 AND d.trade_date <= $2
            ORDER BY d.trade_date DESC
            LIMIT $3
            """,
            ts_code,
            end_date,
            days,
        )

    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        return df
    return df.sort_values("trade_date").reset_index(drop=True)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算技术指标，基于前复权价格（*_qfq 列）。返回新 DataFrame，包含原始列 + 指标列。"""
    out = df.copy()
    out["ma5"] = ta.sma(out["close_qfq"], length=5)
    out["ma10"] = ta.sma(out["close_qfq"], length=10)
    out["ma20"] = ta.sma(out["close_qfq"], length=20)
    out["ma60"] = ta.sma(out["close_qfq"], length=60)
    # ta.macd 返回 3 列：MACD_12_26_9 (DIF), MACDs_12_26_9 (DEA), MACDh_12_26_9 (HIST)
    # 数据量不足 33 天时 ta.macd 返回 None，此时三列全填 NaN
    macd = ta.macd(out["close_qfq"])
    if macd is None:
        out["dif"] = pd.NA
        out["dea"] = pd.NA
        out["hist"] = pd.NA
    else:
        out["dif"] = macd["MACD_12_26_9"]
        out["dea"] = macd["MACDs_12_26_9"]
        out["hist"] = macd["MACDh_12_26_9"]
    out["rsi14"] = ta.rsi(out["close_qfq"], length=14)
    out["atr14"] = ta.atr(out["high_qfq"], out["low_qfq"], out["close_qfq"], length=14)
    out["vol_ma5"] = out["vol"].rolling(5).mean()
    out["vol_ratio_5"] = out["vol"] / out["vol_ma5"]
    return out


async def load_with_indicators(
    ts_code: str, end_date: date, days: int = LOOKBACK_DAYS
) -> pd.DataFrame:
    """加载日线数据并叠加技术指标。"""
    df = await load_daily(ts_code, end_date, days)
    if df.empty:
        return df
    df_qfq = to_qfq(df)
    df_indicators = add_indicators(df_qfq)
    return df_indicators
