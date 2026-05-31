-- 007: create stk_limit_cn table
-- A-share daily price limit (涨跌停价), aligned with Tushare stk_limit API.
-- Source: pro.stk_limit(trade_date='YYYYMMDD')
-- Units: all prices in 元 (no conversion needed)
-- Usage:
--   涨停判定: daily_cn.close == stk_limit_cn.up_limit
--   跌停判定: daily_cn.close == stk_limit_cn.down_limit
--   注意：科创板/创业板/北交所涨跌幅 ±20%，主板 ±10%，ST 股 ±5%

CREATE TABLE stk_limit_cn (
    ts_code      VARCHAR(16)      NOT NULL,            -- 000001.SZ
    trade_date   DATE             NOT NULL,            -- 交易日期
    up_limit     DOUBLE PRECISION NOT NULL,            -- 涨停价（元）
    down_limit   DOUBLE PRECISION NOT NULL,            -- 跌停价（元）
    created_at   TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ts_code, trade_date)
);

CREATE INDEX idx_stk_limit_cn_trade_date ON stk_limit_cn (trade_date);
