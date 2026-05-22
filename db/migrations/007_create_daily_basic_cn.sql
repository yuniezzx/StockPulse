-- 007: create daily_basic_cn table
-- A 股日度基础指标（估值/换手/市值），对齐 Tushare daily_basic API。
-- Source: pro.daily_basic(trade_date=YYYYMMDD)
--
-- 单位约定:
--   close:                       元（不复权）
--   turnover_rate / dv_ratio:    %（保留原值，3.5 表示 3.5%）
--   pe / pb / ps / volume_ratio: 倍数（无单位）
--   total_share / float_share / free_share: 股（万股 × 10000）
--   total_mv / circ_mv:          元（万元 × 10000）
--
-- 主键: (ts_code, trade_date)
-- 业务索引:
--   trade_date：按日查询
--   (trade_date, circ_mv)：选股按流通市值过滤
--   (trade_date, turnover_rate)：选股按活跃度过滤
CREATE TABLE
    daily_basic_cn (
        ts_code         VARCHAR(16)      NOT NULL,
        trade_date      DATE             NOT NULL,
        close           DOUBLE PRECISION,
        turnover_rate   DOUBLE PRECISION,
        turnover_rate_f DOUBLE PRECISION,
        volume_ratio    DOUBLE PRECISION,
        pe              DOUBLE PRECISION,
        pe_ttm          DOUBLE PRECISION,
        pb              DOUBLE PRECISION,
        ps              DOUBLE PRECISION,
        ps_ttm          DOUBLE PRECISION,
        dv_ratio        DOUBLE PRECISION,
        dv_ttm          DOUBLE PRECISION,
        total_share     DOUBLE PRECISION,
        float_share     DOUBLE PRECISION,
        free_share      DOUBLE PRECISION,
        total_mv        DOUBLE PRECISION,
        circ_mv         DOUBLE PRECISION,
        created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );

CREATE INDEX idx_daily_basic_cn_trade_date ON daily_basic_cn (trade_date);
CREATE INDEX idx_daily_basic_cn_circ_mv    ON daily_basic_cn (trade_date, circ_mv);
CREATE INDEX idx_daily_basic_cn_turnover   ON daily_basic_cn (trade_date, turnover_rate);
