-- 005_create_adj_factor_cn.sql
CREATE TABLE
    adj_factor_cn (
        ts_code      VARCHAR(16)      NOT NULL,
        trade_date   DATE             NOT NULL,
        adj_factor   DOUBLE PRECISION NOT NULL,
        created_at   TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );
    
CREATE INDEX idx_adj_factor_cn_trade_date ON adj_factor_cn (trade_date);