-- 008: create moneyflow_cn table
-- A-share individual stock money flow, aligned with Tushare moneyflow API.
-- Source: pro.moneyflow(trade_date='YYYYMMDD')
-- Unit normalization: 手 → 股 (× 100), 万元 → 元 (× 10000)
-- 单类规则:
--   小单 sm: < 5万元
--   中单 md: 5万 - 20万元
--   大单 lg: 20万 - 100万元
--   特大单 elg: ≥ 100万元
-- 主力定义: 大单 + 特大单（在 screener 中组合，不落表）

CREATE TABLE moneyflow_cn (
    ts_code         VARCHAR(16)      NOT NULL,            -- 000001.SZ
    trade_date      DATE             NOT NULL,            -- 交易日期
    buy_sm_vol      DOUBLE PRECISION,                     -- 小单买入量（股，手 × 100）
    buy_sm_amount   DOUBLE PRECISION,                     -- 小单买入额（元，万元 × 10000）
    sell_sm_vol     DOUBLE PRECISION,                     -- 小单卖出量（股）
    sell_sm_amount  DOUBLE PRECISION,                     -- 小单卖出额（元）
    buy_md_vol      DOUBLE PRECISION,                     -- 中单买入量（股）
    buy_md_amount   DOUBLE PRECISION,                     -- 中单买入额（元）
    sell_md_vol     DOUBLE PRECISION,                     -- 中单卖出量（股）
    sell_md_amount  DOUBLE PRECISION,                     -- 中单卖出额（元）
    buy_lg_vol      DOUBLE PRECISION,                     -- 大单买入量（股）
    buy_lg_amount   DOUBLE PRECISION,                     -- 大单买入额（元）
    sell_lg_vol     DOUBLE PRECISION,                     -- 大单卖出量（股）
    sell_lg_amount  DOUBLE PRECISION,                     -- 大单卖出额（元）
    buy_elg_vol     DOUBLE PRECISION,                     -- 特大单买入量（股）
    buy_elg_amount  DOUBLE PRECISION,                     -- 特大单买入额（元）
    sell_elg_vol    DOUBLE PRECISION,                     -- 特大单卖出量（股）
    sell_elg_amount DOUBLE PRECISION,                     -- 特大单卖出额（元）
    net_mf_vol      DOUBLE PRECISION,                     -- 净流入量（股，可负）
    net_mf_amount   DOUBLE PRECISION,                     -- 净流入额（元，可负）
    created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ts_code, trade_date)
);

CREATE INDEX idx_moneyflow_cn_trade_date ON moneyflow_cn (trade_date);
CREATE INDEX idx_moneyflow_cn_net_amount ON moneyflow_cn (trade_date, net_mf_amount);  -- 选股按主力净流入排序
