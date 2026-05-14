-- 006_create_daily_basic_cn.sql
-- Source: Tushare pro.daily_basic(trade_date=...)
-- Units normalized: 万股 → 股 (× 10000), 万元 → 元 (× 10000)

CREATE TABLE daily_basic_cn (
    ts_code          VARCHAR(16)      NOT NULL,
    trade_date       DATE             NOT NULL,
    close            DOUBLE PRECISION,
    turnover_rate    DOUBLE PRECISION,
    turnover_rate_f  DOUBLE PRECISION,
    volume_ratio     DOUBLE PRECISION,
    pe               DOUBLE PRECISION,
    pe_ttm           DOUBLE PRECISION,
    pb               DOUBLE PRECISION,
    ps               DOUBLE PRECISION,
    ps_ttm           DOUBLE PRECISION,
    dv_ratio         DOUBLE PRECISION,
    dv_ttm           DOUBLE PRECISION,
    total_share      DOUBLE PRECISION,
    float_share      DOUBLE PRECISION,
    free_share       DOUBLE PRECISION,
    total_mv         DOUBLE PRECISION,
    circ_mv          DOUBLE PRECISION,
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ts_code, trade_date)
);

CREATE INDEX idx_daily_basic_cn_trade_date ON daily_basic_cn (trade_date);
CREATE INDEX idx_daily_basic_cn_circ_mv ON daily_basic_cn (trade_date, circ_mv);
CREATE INDEX idx_daily_basic_cn_turnover ON daily_basic_cn (trade_date, turnover_rate);
