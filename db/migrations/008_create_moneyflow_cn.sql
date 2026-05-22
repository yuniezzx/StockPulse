-- 008: create moneyflow_cn table
-- A 股个股资金流向，对齐 Tushare moneyflow API。
-- Source: pro.moneyflow(trade_date=YYYYMMDD)
--
-- 单位约定:
--   vol 类（*_vol）:    股（手 × 100）
--   amount 类（*_amount/net_mf_amount）: 元（万元 × 10000）
--
-- 单类规则:
--   小单 sm:  < 5 万元
--   中单 md:  5万 – 20万元
--   大单 lg:  20万 – 100万元
--   特大单 elg: ≥ 100 万元
-- 主力 = 大单 + 特大单（在 screener 中组合，不落表）。
--
-- 主键: (ts_code, trade_date)
-- 业务索引:
--   trade_date：按日查询
--   (trade_date, net_mf_amount)：选股按主力净流入排序
CREATE TABLE
    moneyflow_cn (
        ts_code         VARCHAR(16)      NOT NULL,
        trade_date      DATE             NOT NULL,
        buy_sm_vol      DOUBLE PRECISION,
        buy_sm_amount   DOUBLE PRECISION,
        sell_sm_vol     DOUBLE PRECISION,
        sell_sm_amount  DOUBLE PRECISION,
        buy_md_vol      DOUBLE PRECISION,
        buy_md_amount   DOUBLE PRECISION,
        sell_md_vol     DOUBLE PRECISION,
        sell_md_amount  DOUBLE PRECISION,
        buy_lg_vol      DOUBLE PRECISION,
        buy_lg_amount   DOUBLE PRECISION,
        sell_lg_vol     DOUBLE PRECISION,
        sell_lg_amount  DOUBLE PRECISION,
        buy_elg_vol     DOUBLE PRECISION,
        buy_elg_amount  DOUBLE PRECISION,
        sell_elg_vol    DOUBLE PRECISION,
        sell_elg_amount DOUBLE PRECISION,
        net_mf_vol      DOUBLE PRECISION,
        net_mf_amount   DOUBLE PRECISION,
        created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );

CREATE INDEX idx_moneyflow_cn_trade_date ON moneyflow_cn (trade_date);
CREATE INDEX idx_moneyflow_cn_net_amount ON moneyflow_cn (trade_date, net_mf_amount);
