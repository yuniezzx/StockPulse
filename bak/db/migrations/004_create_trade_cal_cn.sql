-- 004: create trade_cal_cn table
-- A-share trading calendar, aligned with Tushare trade_cal API.
-- Source: pro.trade_cal(exchange='SSE'|'SZSE', start_date, end_date)
--
-- Notes:
--   - exchange:      SSE (上交所) / SZSE (深交所)
--   - is_open:       0 = 休市, 1 = 交易
--   - pretrade_date: 上一个交易日 (休市日也有值，指向最近的交易日)
CREATE TABLE
    trade_cal_cn (
        exchange      TEXT        NOT NULL,                -- SSE / SZSE
        cal_date      DATE        NOT NULL,                -- 日历日期
        is_open       SMALLINT    NOT NULL,                -- 0 = 休市, 1 = 交易
        pretrade_date DATE,                                -- 上一个交易日（休市日也有值）
        created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (exchange, cal_date)
    );
