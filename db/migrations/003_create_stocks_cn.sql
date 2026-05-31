-- 003: create stocks_cn table
-- A 股股票基础元数据，对齐 Tushare stock_basic API。
-- Source: pro.stock_basic(exchange='', list_status='L', fields=...)
--
-- 字段说明:
--   ts_code:      Tushare 股票代码（主键）
--   symbol:       6 位股票代码
--   exchange:     SSE / SZSE / BSE
--   list_status:  L = 上市（当前仅同步上市股）
--   list_date:    上市日期
--   delist_date:  退市日期
--
-- 主键: ts_code
-- 单位: 无（证券主数据表）
CREATE TABLE
    stocks_cn (
        ts_code      VARCHAR(16) PRIMARY KEY,
        symbol       VARCHAR(16) NOT NULL,
        name         VARCHAR(128) NOT NULL,
        fullname     VARCHAR(255),
        enname       VARCHAR(255),
        cnspell      VARCHAR(32),
        area         VARCHAR(64),
        industry     VARCHAR(64),
        market       VARCHAR(16),
        exchange     VARCHAR(8) NOT NULL,
        curr_type    CHAR(3),
        list_status  CHAR(1) NOT NULL,
        list_date    DATE,
        delist_date  DATE,
        is_hs        CHAR(1),
        act_name     VARCHAR(128),
        act_ent_type VARCHAR(16),
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

CREATE INDEX idx_stocks_cn_symbol ON stocks_cn (symbol);

CREATE INDEX idx_stocks_cn_industry ON stocks_cn (industry);

CREATE INDEX idx_stocks_cn_list_status ON stocks_cn (list_status);
