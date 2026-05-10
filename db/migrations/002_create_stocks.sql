-- 002: create stocks table
-- Multi-market security master data 
CREATE TABLE
    stocks (
        symbol VARCHAR(16) PRIMARY KEY,
        market VARCHAR(8) NOT NULL DEFAULT 'A',
        name VARCHAR(128) NOT NULL,
        exchange VARCHAR(8) NOT NULL,
        currency CHAR(3) NOT NULL DEFAULT 'CNY',
        board VARCHAR(16),
        industry VARCHAR(64),
        area VARCHAR(64),
        list_date DATE,
        list_status CHAR(1) NOT NULL DEFAULT 'L',
        cnspell VARCHAR(16),
        is_hs CHAR(1),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW (),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW ()
    );

CREATE INDEX idx_stocks_market ON stocks (market);

CREATE INDEX idx_stocks_name ON stocks (name);

CREATE INDEX idx_stocks_list_status ON stocks (list_status);