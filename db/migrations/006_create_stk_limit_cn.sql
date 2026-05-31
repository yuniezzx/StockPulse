-- 006: create stk_limit_cn table
-- A 股日度涨跌停价，对齐 Tushare stk_limit API。
-- Source: pro.stk_limit(trade_date=YYYYMMDD)
--
-- 字段说明:
--   ts_code:    Tushare 股票代码
--   trade_date: 交易日期
--   up_limit:   涨停价（元）
--   down_limit: 跌停价（元）
--
-- 主键: (ts_code, trade_date)
-- 单位约定: 价格=元（无转换）
-- 用法:
--   涨停判定: daily_cn.close = stk_limit_cn.up_limit
--   跌停判定: daily_cn.close = stk_limit_cn.down_limit
-- 注意: 科创板/创业板/北交所 ±20%，主板 ±10%，ST ±5%
CREATE TABLE
    stk_limit_cn (
        ts_code    VARCHAR(16)      NOT NULL,
        trade_date DATE             NOT NULL,
        up_limit   DOUBLE PRECISION NOT NULL,
        down_limit DOUBLE PRECISION NOT NULL,
        created_at TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );

CREATE INDEX idx_stk_limit_cn_trade_date ON stk_limit_cn (trade_date);
