-- 005: create adj_factor_cn table
-- A 股日度复权因子，对齐 Tushare adj_factor API。
-- Source: pro.adj_factor(trade_date=YYYYMMDD)
--
-- 字段说明:
--   ts_code:    Tushare 股票代码
--   trade_date: 交易日期
--   adj_factor: 复权因子，单位=无
--
-- 主键: (ts_code, trade_date)
-- 单位约定: 复权因子=无单位
-- 用法:
--   后复权价 = 原始价 × adj_factor
--   前复权价 = 原始价 × adj_factor / 最新 adj_factor
CREATE TABLE
    adj_factor_cn (
        ts_code    VARCHAR(16)      NOT NULL,
        trade_date DATE             NOT NULL,
        adj_factor DOUBLE PRECISION NOT NULL,
        created_at TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );

CREATE INDEX idx_adj_factor_cn_trade_date ON adj_factor_cn (trade_date);
