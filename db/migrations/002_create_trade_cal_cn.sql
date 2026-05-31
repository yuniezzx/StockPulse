-- 002: create trade_cal_cn table
-- A 股交易日历，对齐 Tushare trade_cal API。
-- Source: pro.trade_cal(exchange='SSE'|'SZSE', start_date, end_date)
--
-- 字段说明:
--   exchange:      SSE (上交所) / SZSE (深交所)
--   cal_date:      日历日期
--   is_open:       0 = 休市, 1 = 交易
--   pretrade_date: 上一个交易日 (休市日也有值，指向最近的交易日)
--
-- 主键: (exchange, cal_date)
-- 单位: 无（纯日历表）
CREATE TABLE
    trade_cal_cn (
        exchange      TEXT        NOT NULL,
        cal_date      DATE        NOT NULL,
        is_open       SMALLINT    NOT NULL,
        pretrade_date DATE,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (exchange, cal_date)
    );

CREATE INDEX idx_trade_cal_cn_open ON trade_cal_cn (exchange, is_open, cal_date);
