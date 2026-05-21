-- 002: create stocks_cn table
-- A-share security master data, aligned with Tushare stock_basic API.
-- HK/US stocks will live in separate tables (stocks_hk, stocks_us).
CREATE TABLE
    stocks_cn (
        ts_code      VARCHAR(16) PRIMARY KEY,        -- 000001.SZ
        symbol       VARCHAR(16) NOT NULL,           -- 000001
        name         VARCHAR(128) NOT NULL,
        fullname     VARCHAR(255),                   -- 公司全称
        enname       VARCHAR(255),                   -- 英文名
        cnspell      VARCHAR(32),                    -- 拼音首字母
        area         VARCHAR(64),                    -- 地域
        industry     VARCHAR(64),                    -- 所属行业
        market       VARCHAR(16),                    -- 板块：主板/创业板/科创板/CDR/北交所
        exchange     VARCHAR(8) NOT NULL,            -- SSE/SZSE/BSE
        curr_type    CHAR(3),                        -- CNY
        list_status  CHAR(1) NOT NULL,               -- L上市 / D退市 / P暂停
        list_date    DATE,
        delist_date  DATE,
        is_hs        CHAR(1),                        -- N否 / H沪股通 / S深股通
        act_name     VARCHAR(128),                   -- 实际控制人
        act_ent_type VARCHAR(16),                    -- 实控人类型
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

CREATE INDEX idx_stocks_cn_symbol   ON stocks_cn (symbol);
CREATE INDEX idx_stocks_cn_industry ON stocks_cn (industry);
