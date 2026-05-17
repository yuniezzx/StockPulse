-- 009: create daily_picks table
-- 选股结果中央仓库：每个策略每日选出的股票，作为系统输出层。
-- 漏斗式选股的第一层产物，给 Web 展示与通知推送消费。
-- 主键 (trade_date, ts_code, strategy)：同一只股可被多个策略同时选中（多策略共振）。

CREATE TABLE daily_picks (
    trade_date       DATE             NOT NULL,            -- 选股日期
    ts_code          VARCHAR(16)      NOT NULL,            -- 股票代码 000001.SZ
    strategy         VARCHAR(32)      NOT NULL,            -- 策略名 breakout / pullback / macd_cross / limit_up / moneyflow
    score            DOUBLE PRECISION NOT NULL,            -- 该策略打分（用于排名，越高越优）
    rank_in_strategy INTEGER          NOT NULL,            -- 该策略当日排名（1 = 最优）
    signals          JSONB            NOT NULL DEFAULT '{}'::jsonb,  -- 触发信号详情（解释"为什么选它"）
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    PRIMARY KEY (trade_date, ts_code, strategy)
);

CREATE INDEX idx_daily_picks_date_strategy_rank
    ON daily_picks (trade_date, strategy, rank_in_strategy);  -- 单策略 top N 查询
CREATE INDEX idx_daily_picks_date_score
    ON daily_picks (trade_date, score DESC);                  -- 跨策略综合排序
CREATE INDEX idx_daily_picks_ts_code
    ON daily_picks (ts_code, trade_date DESC);                -- 单股历史被选记录
