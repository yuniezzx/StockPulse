-- 004: create daily_cn table
-- A 股日线 OHLCV 行情，对齐 Tushare daily API。
-- Source: pro.daily(trade_date=YYYYMMDD)
--
-- 字段说明:
--   ts_code:    Tushare 股票代码
--   trade_date: 交易日期
--   open/high/low/close/pre_close/change: 价格字段，单位=元
--   pct_chg:    涨跌幅，单位=%
--   vol:        成交量，单位=股（Tushare vol × 100）
--   amount:     成交额，单位=元（Tushare amount × 1000）
--
-- 主键: (ts_code, trade_date)
-- 单位约定: 价格=元，涨跌幅=%，成交量=股，成交额=元
CREATE TABLE
    daily_cn (
        ts_code    VARCHAR(16)      NOT NULL,
        trade_date DATE             NOT NULL,
        open       DOUBLE PRECISION,
        high       DOUBLE PRECISION,
        low        DOUBLE PRECISION,
        close      DOUBLE PRECISION,
        pre_close  DOUBLE PRECISION,
        change     DOUBLE PRECISION,
        pct_chg    DOUBLE PRECISION,
        vol        DOUBLE PRECISION,
        amount     DOUBLE PRECISION,
        created_at TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );

CREATE INDEX idx_daily_cn_trade_date ON daily_cn (trade_date);
