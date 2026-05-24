-- 012: create daily_volume_indicators_cn table
-- A 股日度量价与估值指标，派生数据层。
-- Source: pulse_core.indicators.compute（基于 daily_cn + daily_basic_cn + adj_factor_cn）
--
-- 字段说明:
--   ts_code:                  Tushare 股票代码
--   trade_date:               交易日期
--   vol_ma5/vol_ma10:         成交量移动平均（基于 vol_qfq），单位=股
--   vol_ratio_5:              量比 = vol_qfq / vol_ma5，单位=无
--   turnover_rate_ma5:        换手率 5 日均值（基于 daily_basic_cn.turnover_rate），单位=%（3.5 表示 3.5%）
--   turnover_rate_ratio_5:    换手放大倍数 = 当日 turnover_rate / turnover_rate_ma5，单位=无
--   pe_ttm_pct_60:            PE_TTM 60 日分位（0.0-1.0，0.2 表示当前 PE 处于近 60 日 20% 分位）
--   pb_pct_60:                PB 60 日分位（0.0-1.0）
--
-- 主键: (ts_code, trade_date)
-- 单位约定: vol_ma=股，量比/换手放大倍数=无单位，turnover_rate=%，分位列=小数 [0,1]
-- NULL 语义:
--   vol_ma5 == 0 时 vol_ratio_5 = NULL（除零防御）
--   分位列窗口期不足 → NULL
--   daily_basic_cn 缺失行（停牌等）→ 整行不写
CREATE TABLE
    daily_volume_indicators_cn (
        ts_code               VARCHAR(16)      NOT NULL,
        trade_date            DATE             NOT NULL,
        vol_ma5               DOUBLE PRECISION,
        vol_ma10              DOUBLE PRECISION,
        vol_ratio_5           DOUBLE PRECISION,
        turnover_rate_ma5     DOUBLE PRECISION,
        turnover_rate_ratio_5 DOUBLE PRECISION,
        pe_ttm_pct_60         DOUBLE PRECISION,
        pb_pct_60             DOUBLE PRECISION,
        created_at            TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );
CREATE INDEX idx_daily_volume_indicators_cn_trade_date ON daily_volume_indicators_cn (trade_date);