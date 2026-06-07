-- 014: create daily_scorecards table
-- 全市场每日股票通用打分快照，scorecard 子系统派生数据层。
-- Source: pulse_core.scorecard.runner（基于 daily_*_indicators_cn 计算）
--
-- 字段说明:
--   trade_date:  交易日期
--   ts_code:     Tushare 股票代码
--   scorecard:   JSONB，Scorecard pydantic 模型序列化结果
--                结构 = { version, dimensions: {key: {score, kind, details}}, metadata }
--                完整契约见 docs/scorecard.md §9
--
-- 主键: (trade_date, ts_code) — 一票一日一行
-- 不冗余存最终得分:
--   weighted_score 因 track.weights 不同而不同，由 runner 实时计算后写入 daily_picks
--   前端展示综合得分时需指定 track（或同时展示多 track 分数）
-- JSONB 校验:
--   Scorecard 结构由 pulse-core pydantic v2 在写入前校验
--   DB 层不做 JSONB schema 约束（依赖 pulse-core 单一写入方）
CREATE TABLE
    daily_scorecards (
        trade_date  DATE         NOT NULL,
        ts_code     VARCHAR(16)  NOT NULL,
        scorecard   JSONB        NOT NULL,
        created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        PRIMARY KEY (trade_date, ts_code)
    );
CREATE INDEX idx_daily_scorecards_ts_code ON daily_scorecards (ts_code);