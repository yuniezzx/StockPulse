-- 011: create daily_momentum_indicators_cn table
-- A 股日度动量与事件指标（摆动 + 波动 + 形态事件），派生数据层。
-- Source: pulse_core.indicators.compute（基于 daily_cn + adj_factor_cn + stk_limit_cn）
--
-- 字段说明:
--   ts_code:           Tushare 股票代码
--   trade_date:        交易日期
--   rsi6:              RSI(6) Wilder 平滑，短线超买超卖，取值 [0, 100]
--   rsi12:             RSI(12) Wilder 平滑，中线
--   rsi24:             RSI(24) Wilder 平滑，长线
--   is_rsi_bull_arrangement: RSI 多头排列（rsi6 > rsi12 > rsi24），首日 NULL
--   atr14:             ATR(14) Wilder 平滑（基于 qfq high/low/close），单位=元
--   pct_chg_5d:        5 个交易日累计涨跌幅（基于 close_qfq），单位=%（0.05 表示 5%）
--   pct_chg_20d:       20 个交易日累计涨跌幅，单位同上
--   gap_pct:           跳空缺口百分比 = (open - pre_close) / pre_close，单位同上
--   body_pct:          K 线实体大小 = abs(close - open) / open，单位同上
--   is_new_high_60d:   60 日新高客观标记（close == 60 日最高 close）
--   is_new_low_60d:    60 日新低客观标记
--   is_limit_up:       涨停客观标记（|close - up_limit| < 0.01）
--   is_limit_down:     跌停客观标记（|close - down_limit| < 0.01）
--
-- 主键: (ts_code, trade_date)
-- 单位约定: RSI(6/12/24)=百分比刻度 [0,100]，ATR=元，pct_chg/gap/body=小数百分比（0.05=5%）
-- NULL 语义:
--   数值列窗口期不足 → NULL
--   布尔列首日 → NULL（无法判定）
--   缺失 stk_limit_cn → is_limit_up/down = FALSE（业务语义）
-- 涨跌停说明: 用原始 close 与 up_limit/down_limit 比较，不用 qfq（限价是原始价）
-- RSI 周期沿用同花顺/东方财富 A 股惯例（6/12/24）
CREATE TABLE
    daily_momentum_indicators_cn (
        ts_code         VARCHAR(16)      NOT NULL,
        trade_date      DATE             NOT NULL,
        rsi6                      DOUBLE PRECISION,
        rsi12                     DOUBLE PRECISION,
        rsi24                     DOUBLE PRECISION,
        is_rsi_bull_arrangement   BOOLEAN,
        atr14                     DOUBLE PRECISION,
        pct_chg_5d      DOUBLE PRECISION,
        pct_chg_20d     DOUBLE PRECISION,
        gap_pct         DOUBLE PRECISION,
        body_pct        DOUBLE PRECISION,
        is_new_high_60d BOOLEAN,
        is_new_low_60d  BOOLEAN,
        is_limit_up     BOOLEAN,
        is_limit_down   BOOLEAN,
        created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );
CREATE INDEX idx_daily_momentum_indicators_cn_trade_date ON daily_momentum_indicators_cn (trade_date);
