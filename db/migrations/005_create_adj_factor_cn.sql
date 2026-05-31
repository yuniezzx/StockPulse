-- 005: create adj_factor_cn table
-- A-share daily adjustment factor, aligned with Tushare adj_factor API.
-- Usage:
--   后复权价 = 原始价 × adj_factor
--   前复权价 = 原始价 × adj_factor / 最新 adj_factor
CREATE TABLE
    adj_factor_cn (
        ts_code      VARCHAR(16)      NOT NULL,            -- 000001.SZ
        trade_date   DATE             NOT NULL,            -- 交易日期
        adj_factor   DOUBLE PRECISION NOT NULL,            -- 复权因子（无单位）
        created_at   TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );

CREATE INDEX idx_adj_factor_cn_trade_date ON adj_factor_cn (trade_date);
