-- 006: create daily_basic_cn table
-- A-share daily valuation / turnover / market-cap metrics, aligned with Tushare daily_basic API.
-- Units normalized: 万股 → 股 (× 10000), 万元 → 元 (× 10000)
-- 百分比字段保留原值（如 turnover_rate=3.5 表示 3.5%）

CREATE TABLE daily_basic_cn (
    ts_code          VARCHAR(16)      NOT NULL,            -- 000001.SZ
    trade_date       DATE             NOT NULL,            -- 交易日期
    close            DOUBLE PRECISION,                     -- 当日收盘价（元，不复权）
    turnover_rate    DOUBLE PRECISION,                     -- 换手率 %
    turnover_rate_f  DOUBLE PRECISION,                     -- 换手率 %（自由流通股本口径）
    volume_ratio     DOUBLE PRECISION,                     -- 量比 = 当日量 / 过去5日均量
    pe               DOUBLE PRECISION,                     -- 市盈率（亏损股可能为负或 NULL）
    pe_ttm           DOUBLE PRECISION,                     -- 市盈率 TTM（滚动12月净利）
    pb               DOUBLE PRECISION,                     -- 市净率
    ps               DOUBLE PRECISION,                     -- 市销率
    ps_ttm           DOUBLE PRECISION,                     -- 市销率 TTM
    dv_ratio         DOUBLE PRECISION,                     -- 股息率 %
    dv_ttm           DOUBLE PRECISION,                     -- 股息率 TTM %
    total_share      DOUBLE PRECISION,                     -- 总股本（股，万股 × 10000）
    float_share      DOUBLE PRECISION,                     -- 流通股本（股）
    free_share       DOUBLE PRECISION,                     -- 自由流通股本（股）
    total_mv         DOUBLE PRECISION,                     -- 总市值（元，万元 × 10000）
    circ_mv          DOUBLE PRECISION,                     -- 流通市值（元）
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ts_code, trade_date)
);

CREATE INDEX idx_daily_basic_cn_trade_date ON daily_basic_cn (trade_date);
CREATE INDEX idx_daily_basic_cn_circ_mv    ON daily_basic_cn (trade_date, circ_mv);     -- 选股按市值过滤
CREATE INDEX idx_daily_basic_cn_turnover   ON daily_basic_cn (trade_date, turnover_rate); -- 选股按活跃度过滤
