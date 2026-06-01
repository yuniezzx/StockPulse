-- 014: create daily_picks table (v2.0)
-- pulse-core screener 每晚选股的最终结果，圈 3 自动业务数据（architecture.md §5.1 漏斗末端）。
-- 一行 = 一只股票在一个赛道被一个策略命中（已通过 Layer 1/2 过滤 + Layer 3 打分截 top N）。
-- 共振汇总（同一票被多策略/多赛道命中）由后续视图聚合产生，不在本表冗余。
--
-- 用途：存放每日各赛道、各策略的入选股票及其打分卡。
-- 主键设计意图：(trade_date, track, strategy, ts_code) 自然唯一；按日横向查询为主，
--               track / strategy 前置利于分赛道/分策略过滤。
-- 单位换算：score / reward_score / risk_score / final_score = 无单位（0~100，越高越好）；
--           w_reward / w_risk = 无单位（0~1，权重和 ≤ 1.00 预留未来 axis 扩展空间）。
--
-- ─────────────────────────────────────────────────────────────────────
-- 字段说明
-- ─────────────────────────────────────────────────────────────────────
--   trade_date    : 交易日期
--   track         : 赛道 key，snake_case，与 screener/tracks/{track}.yaml 文件名一致
--                   内置: scalp（超短）/ swing（波段）/ position（中线）
--   strategy      : 策略 key，snake_case，与 pulse_core 中 Strategy.name 一致
--                   跨语言契约：DB strategy ↔ Python Strategy.name ↔ TS strategy-meta.ts key
--   ts_code       : Tushare 股票代码
--   reward_score  : reward 轴综合得分 [0, 100]
--   risk_score    : risk 轴综合得分 [0, 100]（风险规避分；越高越安全）
--   final_score   : 双轴加权终分 = w_reward * reward_score + w_risk * risk_score
--   w_reward      : reward 轴权重 [0, 1]，本期默认 0.70
--   w_risk        : risk   轴权重 [0, 1]，本期默认 0.30
--   scorecard     : 评分卡（JSONB，必填）—— 策略一次性产出，前端用于渲染"为什么入选+风险点"
--   signals       : 漏斗累积日志（JSONB，可选）—— Filter/Strategy 各阶段追加，仅用于调试审计
--   created_at    : 行写入时间
--
-- ─────────────────────────────────────────────────────────────────────
-- 双轴加权设计（详见 docs/screener.md §4）
-- ─────────────────────────────────────────────────────────────────────
-- reward 与 risk 独立打分、独立加权，再合成 final_score。
-- 权重 (w_reward, w_risk) 同时升列（DB 查询 / 排序友好）并镜像写入 scorecard.axis_weights
-- （JSONB 自描述、前端渲染友好）—— 列与 JSONB 互为冗余但语义一致，由策略保证同步。
--
-- 约束 w_reward + w_risk <= 1.00 而非 = 1.00 的原因：
--   预留未来扩展第 3 轴（如 momentum / event 等）的空间，无需 ALTER TABLE。
--
-- ─────────────────────────────────────────────────────────────────────
-- scorecard JSONB 契约（v2.0）
-- ─────────────────────────────────────────────────────────────────────
-- 形状:
-- {
--   "axis_weights":    { "reward": 0.70, "risk": 0.30 },              -- 与列 w_reward/w_risk 镜像
--   "axis_scores":     { "reward": 86.40, "risk": 85.00, "final": 85.98 }, -- 与列同名 score 镜像
--   "reward_dimensions": {
--     "<dim_key>": {
--       "score":   <0-100>,        -- NUMERIC(5,2) 序列化为 JSON number，2 位小数
--       "weight":  <0-1>,          -- NUMERIC(3,2)，该维度在 reward 轴内的权重
--       "details": { ... }         -- 维度专属明细，snake_case keys，schema 由策略自管
--     }
--   },
--   "risk_dimensions": {
--     "<dim_key>": {
--       "score":   <0-100>,        -- 风险规避分，越高越安全
--       "weight":  <0-1>,          -- 该维度在 risk 轴内的权重
--       "source":  "shared:liquidity_risk" | "strategy:<strategy_name>",  -- 必填，区分共享/策略私有
--       "details": { ... }
--     }
--   }
-- }
--
-- 强制规则:
--   1. axis_weights / axis_scores / reward_dimensions / risk_dimensions 四个 key 必须存在
--   2. risk_dimensions 至少包含 1 个维度
--   3. risk_dimensions 至少包含 1 个 source 以 "shared:" 开头的维度
--      （本期等价于必含 shared:liquidity_risk，未来共享维度扩展后规则自然放宽）
--   4. 每个 dimension.weight 之和 ≈ 1.0（该轴内权重归一），容差 1e-6
--   5. axis_scores.reward / risk 必须等于对应 dimensions 的加权和（容差 1e-6）
--   6. axis_scores.final 必须等于 w_reward * reward + w_risk * risk（容差 1e-6）
--   7. JSONB 内部 key 全部 snake_case；pulse-api repository 层负责递归 snake → camel 转换
--
-- 命名约定:
--   - dimension_key 全 snake_case（如 limit_up_strength / liquidity_risk）
--   - 共享 risk 维度的 key 后缀建议为 _risk，便于一眼识别
--
-- ─────────────────────────────────────────────────────────────────────
-- signals JSONB 契约（漏斗累积日志，可选）
-- ─────────────────────────────────────────────────────────────────────
-- 与 scorecard 互补：scorecard 是"打分结果"，signals 是"过关日志"。
-- Layer 1/2 Filter 在该股票被拒绝时不写入 daily_picks（自然不会有 signals）；
-- 通过的股票，Strategy 可选择性把关键 Filter 中间值塞进 signals.filters 便于审计。
--
-- 形状:
-- {
--   "filters":  { "<filter_name>": { "passed": true, ... } },
--   "strategy": { "raw_inputs": { ... } }
-- }
--
-- 规范 database.md §3：JSONB 是"逃生舱"，内部无约束；若某子字段查询频繁应升列。
--
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE
    daily_picks (
        trade_date   DATE          NOT NULL,
        track        VARCHAR(16)   NOT NULL,
        strategy     VARCHAR(32)   NOT NULL,
        ts_code      VARCHAR(16)   NOT NULL,
        reward_score NUMERIC(5, 2) NOT NULL,
        risk_score   NUMERIC(5, 2) NOT NULL,
        final_score  NUMERIC(5, 2) NOT NULL,
        w_reward     NUMERIC(3, 2) NOT NULL,
        w_risk       NUMERIC(3, 2) NOT NULL,
        scorecard    JSONB         NOT NULL,
        signals      JSONB,
        created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
        PRIMARY KEY (trade_date, track, strategy, ts_code),
        CONSTRAINT ck_daily_picks_reward_range CHECK (reward_score BETWEEN 0 AND 100),
        CONSTRAINT ck_daily_picks_risk_range   CHECK (risk_score   BETWEEN 0 AND 100),
        CONSTRAINT ck_daily_picks_final_range  CHECK (final_score  BETWEEN 0 AND 100),
        CONSTRAINT ck_daily_picks_w_reward     CHECK (w_reward     BETWEEN 0 AND 1),
        CONSTRAINT ck_daily_picks_w_risk       CHECK (w_risk       BETWEEN 0 AND 1),
        CONSTRAINT ck_daily_picks_axis_weights CHECK (w_reward + w_risk <= 1.00)
    );

-- 二级索引：支持"某只股票在过去 N 天的入选历史"查询（持仓页 / 校验页常用）
CREATE INDEX ix_daily_picks_ts_code_date ON daily_picks (ts_code, trade_date DESC);
