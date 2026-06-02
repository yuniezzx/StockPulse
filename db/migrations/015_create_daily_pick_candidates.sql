-- 015: create daily_pick_candidates table
-- Phase 1+ 扩展：保存 Layer 3 策略打分阶段的**全量结果**（rank ≤ top_n 的子集即 daily_picks）。
--
-- 用途：
--   - 调试：回答"600519 那天为什么没进 top 10"（看 rank 和 score）
--   - 共振分析：跨策略候选池聚合（top_n 之外的边缘候选也参与）
--   - 策略复盘：调整阈值前看完整分布
--
-- 与 daily_picks 的关系：
--   daily_picks ⊆ daily_pick_candidates（rank ≤ top_n 的子集）
--   pulse-core 同事务原子写两张表（保证一致性）
--   daily_picks  → 业务流（早报、虚拟仓、共振汇总）
--   daily_pick_candidates → 调试 / 研究 / 历史回溯
--
-- 保留策略：
--   保留最近 365 天，由后续维护任务（暂未实现）按 trade_date 滚动清理。
--   行数估算：3 赛道 × ~700 候选/赛道/天 × 365 天 ≈ 76 万行（可控）。
--
-- 主键设计：
--   (trade_date, track, strategy, ts_code) —— 与 daily_picks 一致，自然唯一。
--
-- 字段：
--   除 daily_picks 全部字段外，多一列 rank：该 strategy 在该赛道 + 交易日内的排名（1 起，按 final_score DESC）。
--   rank 由 pulse-core 写入时计算并固化，避免下游 ORDER BY 时排序漂移。
--
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE
    daily_pick_candidates (
        trade_date   DATE          NOT NULL,
        track        VARCHAR(16)   NOT NULL,
        strategy     VARCHAR(32)   NOT NULL,
        ts_code      VARCHAR(16)   NOT NULL,
        rank         INTEGER       NOT NULL,
        reward_score NUMERIC(5, 2) NOT NULL,
        risk_score   NUMERIC(5, 2) NOT NULL,
        final_score  NUMERIC(5, 2) NOT NULL,
        w_reward     NUMERIC(3, 2) NOT NULL,
        w_risk       NUMERIC(3, 2) NOT NULL,
        scorecard    JSONB         NOT NULL,
        signals      JSONB,
        created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
        PRIMARY KEY (trade_date, track, strategy, ts_code),
        CONSTRAINT ck_dpc_reward_range CHECK (reward_score BETWEEN 0 AND 100),
        CONSTRAINT ck_dpc_risk_range   CHECK (risk_score   BETWEEN 0 AND 100),
        CONSTRAINT ck_dpc_final_range  CHECK (final_score  BETWEEN 0 AND 100),
        CONSTRAINT ck_dpc_w_reward     CHECK (w_reward     BETWEEN 0 AND 1),
        CONSTRAINT ck_dpc_w_risk       CHECK (w_risk       BETWEEN 0 AND 1),
        CONSTRAINT ck_dpc_axis_weights CHECK (w_reward + w_risk <= 1.00),
        CONSTRAINT ck_dpc_rank_positive CHECK (rank >= 1)
    );

-- 二级索引：支持"某只股票最近的候选历史"查询（调试时常用）
CREATE INDEX ix_dpc_ts_code_date ON daily_pick_candidates (ts_code, trade_date DESC);

-- 二级索引：支持"某天某赛道某策略 top N"查询（rank 升序天然支持）
CREATE INDEX ix_dpc_date_track_strategy_rank
    ON daily_pick_candidates (trade_date, track, strategy, rank);
