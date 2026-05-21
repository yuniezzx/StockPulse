-- 003: create daily_cn table
-- A-share daily OHLCV data, aligned with Tushare daily API.
-- Unit conventions (normalized in ingestion layer):
--   - Price fields (open/high/low/close/pre_close/change): 元
--   - vol:    股 (Tushare 'vol' × 100)
--   - amount: 元 (Tushare 'amount' × 1000)
--   - pct_chg: %
CREATE TABLE
    daily_cn (
        ts_code      VARCHAR(16)      NOT NULL,            -- 000001.SZ
        trade_date   DATE             NOT NULL,            -- 交易日期
        open         DOUBLE PRECISION,                     -- 开盘价（元）
        high         DOUBLE PRECISION,                     -- 最高价（元）
        low          DOUBLE PRECISION,                     -- 最低价（元）
        close        DOUBLE PRECISION,                     -- 收盘价（元，不复权）
        pre_close    DOUBLE PRECISION,                     -- 昨收价（元）
        change       DOUBLE PRECISION,                     -- 涨跌额（元）= close - pre_close
        pct_chg      DOUBLE PRECISION,                     -- 涨跌幅 %（IPO 首日可超 ±10%）
        vol          DOUBLE PRECISION,                     -- 成交量（股，Tushare 'vol' × 100）
        amount       DOUBLE PRECISION,                     -- 成交额（元，Tushare 'amount' × 1000）
        created_at   TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );

CREATE INDEX idx_daily_cn_trade_date ON daily_cn (trade_date);
