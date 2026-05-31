-- 013: create daily_moneyflow_indicators_cn table
-- A 股日度资金流向派生指标，派生数据层。
-- Source: pulse_core.indicators.compute（基于 moneyflow_cn + daily_cn）
--
-- 字段说明:
--   ts_code:                 Tushare 股票代码
--   trade_date:              交易日期
--   main_net_amount:         主力净流入金额 = (buy_lg + buy_elg) - (sell_lg + sell_elg)，单位=元
--   main_net_ratio:          主力净流入占比 = main_net_amount / amount（当日成交额），单位=无（[-1, 1] 区间）
--   main_net_amount_ma5:     主力净流入 5 日均值，单位=元
--   retail_net_amount:       散户净流入金额 = (buy_sm + buy_md) - (sell_sm + sell_md)，单位=元
--
-- 主键: (ts_code, trade_date)
-- 单位约定: 金额列=元，比例列=小数（无单位）
-- NULL 语义:
--   moneyflow_cn 缺失行 → 整行不写
--   amount == 0 时 main_net_ratio = NULL（除零防御）
--   main_net_amount_ma5 窗口期不足 → NULL
-- 单类规则（来自 moneyflow_cn）:
--   小单 sm: <5万；中单 md: 5万–20万；大单 lg: 20万–100万；特大单 elg: ≥100万
--   主力 = 大单 + 特大单（约定，与 moneyflow_cn 注释一致）
CREATE TABLE
    daily_moneyflow_indicators_cn (
        ts_code             VARCHAR(16)      NOT NULL,
        trade_date          DATE             NOT NULL,
        main_net_amount     DOUBLE PRECISION,
        main_net_ratio      DOUBLE PRECISION,
        main_net_amount_ma5 DOUBLE PRECISION,
        retail_net_amount   DOUBLE PRECISION,
        created_at          TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (ts_code, trade_date)
    );
CREATE INDEX idx_daily_moneyflow_indicators_cn_trade_date ON daily_moneyflow_indicators_cn (trade_date);