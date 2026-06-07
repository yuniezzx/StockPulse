-- 015: rebuild daily_picks for scorecard subsystem
-- 各赛道每日按加权分选出的 top N 结果，scorecard 子系统输出层。
-- Source: pulse_core.scorecard.runner（基于 daily_scorecards + tracks/{track}.yaml.weights 实时加权排序）
--
-- 字段说明:
--   trade_date:      交易日期
--   track:           赛道 key（snake_case），必须存在于 pulse_core/scorecard/tracks/*.yaml
--   ts_code:         Tushare 股票代码
--   rank:            赛道内排名（1 = 最佳，最大值 = track.top_n）
--   weighted_score:  按 track.weights 实时计算的加权得分，[0, 100]
--                    公式 = Σ(dim.score × weight) / Σ effective_weights（仅 kind ∈ {signal, risk}）
--                    完整契约见 docs/scorecard.md §5
--   signals:         JSONB，过滤器日志 + 缺失维度追溯
--                    例: {"missing_dimensions": ["volatility"]}
--                    例: {"_filter_liquidity": {"reason": "amount_too_low"}}
--                    无信息时为空对象 {}
--
-- 主键: (trade_date, track, ts_code) — 每只票每 track 每日一行
--
-- 典型查询（取赛道 top N + 关联打分卡）:
--   SELECT p.*, s.scorecard
--   FROM daily_picks p
--   JOIN daily_scorecards s USING (trade_date, ts_code)
--   WHERE p.trade_date = $1 AND p.track = $2
--   ORDER BY p.rank;
CREATE TABLE
    daily_picks (
        trade_date      DATE             NOT NULL,
        track           VARCHAR(32)      NOT NULL,
        ts_code         VARCHAR(16)      NOT NULL,
        rank            INTEGER          NOT NULL CHECK (rank >= 1),
        weighted_score  DOUBLE PRECISION NOT NULL CHECK (weighted_score >= 0 AND weighted_score <= 100),
        signals         JSONB            NOT NULL DEFAULT '{}'::jsonb,
        created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (trade_date, track, ts_code)
    );
CREATE INDEX idx_daily_picks_ts_code ON daily_picks (ts_code);
CREATE INDEX idx_daily_picks_track_score ON daily_picks (trade_date, track, weighted_score DESC);