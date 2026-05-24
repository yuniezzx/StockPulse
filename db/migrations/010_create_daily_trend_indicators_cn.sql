-- 010: create daily_trend_indicators_cn table
-- A 股日度趋势类指标（均线 + MACD 动量交叉），派生数据层。
-- Source: pulse_core.indicators.compute（基于 daily_cn + adj_factor_cn 在 qfq close 上计算）
--
-- 字段说明:
--   ts_code:                Tushare 股票代码
--   trade_date:             交易日期
--   ma5/ma10/ma20/ma60:     移动平均（基于 close_qfq），单位=元
--   ema12/ema26:            指数移动平均（基于 close_qfq），单位=元
--   dif/dea/hist:           MACD 指标（A 股惯例 hist=(dif-dea)*2），单位=元
--   is_macd_golden_cross:   MACD 金叉客观标记（prev dif<=dea AND today dif>dea）
--   is_ma_bull_arrangement: 多头排列客观标记（ma5>ma10>ma20>ma60）
--
-- 主键: (ts_code, trade_date)
-- 单位约定: 价格类列=元
-- NULL 语义:
--   数值列首日/不足窗口期 → NULL（min_periods=window 强制）
--   布尔列首日（无前一日比较）→ NULL（真实反映"无法判定"）
-- 复权策略: 所有列基于 qfq close 计算；qfq 转换在 compute.py 运行时完成，不入此表
CREATE TABLE
    daily_trend_indicators_cn (
        ts_code                VARCHAR(16)      NOT NULL,
        trade_date             DATE             NOT NULL,
        ma5                    DOUBLE PRECISION,
        ma10                   DOUBLE PRECISION,
        ma20                   DOUBLE PRECISION,
        ma60                   DOUBLE PRECISION,
        ema12                  DOUBLE PRECISION,
        ema26                  DOUBLE PRECISION,
        dif                    DOUBLE PRECISION,
        dea                    DOUBLE PRECISION,
        hist                   DOUBLE PRECISION,
        is_macd_golden_cross   BOOLEAN,
        is_ma_bull_arrangement BOOLEAN,
        created_at             TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );
CREATE INDEX idx_daily_trend_indicators_cn_trade_date ON daily_trend_indicators_cn (trade_date);