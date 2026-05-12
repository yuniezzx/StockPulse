-- 003: create daily_cn table
-- A-share daily OHLCV data, aligned with Tushare daily API.
-- Unit conventions (normalized in ingestion layer):
--   - Price fields (open/high/low/close/pre_close/change): 元
--   - vol:    股 (Tushare 'vol' × 100)
--   - amount: 元 (Tushare 'amount' × 1000)
--   - pct_chg: %
CREATE TABLE
    daily_cn (
        ts_code      VARCHAR(16)      NOT NULL,
        trade_date   DATE             NOT NULL,
        open         DOUBLE PRECISION,
        high         DOUBLE PRECISION,
        low          DOUBLE PRECISION,
        close        DOUBLE PRECISION,
        pre_close    DOUBLE PRECISION,
        change       DOUBLE PRECISION,
        pct_chg      DOUBLE PRECISION,
        vol          DOUBLE PRECISION,
        amount       DOUBLE PRECISION,
        created_at   TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );

CREATE INDEX idx_daily_cn_trade_date ON daily_cn (trade_date);