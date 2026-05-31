-- 014: create daily_picks table
-- pulse-core screener 每晚选股的最终结果，圈 3 自动业务数据（架构 §5.1 漏斗末端）。
-- 一行 = 一只股票在一个赛道被一个策略命中（已通过 Layer 1/2 过滤 + Layer 3 打分截 top N）。
-- 共振汇总（同一票被多策略/多赛道命中）由 v_picks_resonance 视图聚合产生，不在本表冗余。
--
-- 字段说明:
--   trade_date: 交易日期
--   track:      赛道 key，snake_case，与 screener/tracks/{track}.yaml 文件名一致
--               内置: scalp（超短）/ swing（波段）/ position（中线）
--   strategy:   策略 key，snake_case，与 pulse_core 中 Strategy.name 一致
--               （跨语言契约：DB strategy ↔ Python Strategy.name ↔ TS strategy-meta.ts key）
--   ts_code:    Tushare 股票代码
--   score:      策略综合排序分，[0, 100]，单位=无；跨策略可比较；
--               与 scorecard 内各维度加权和一致（顶层为单一真理，scorecard 不重复存 final_score）
--   scorecard:  评分卡（JSONB，必填，结构化契约）—— 策略一次性产出，前端用于渲染"为什么入选 + 风险点"
--   signals:    漏斗累积日志（JSONB，可选，半结构化）—— 各阶段（filters/strategy/risk）追加写入，
--               用于调试与审计"为什么通过/为什么没通过"，不参与排序
--   created_at: 行写入时间
--
-- 主键: (trade_date, track, strategy, ts_code)
--   - 按日横向查询为主（前端"今天的候选"）
--   - track / strategy 前置利于按赛道/策略过滤的 partition pruning
--   - ts_code 在末位，因为按日内不需要单股查询
--
-- 单位约定:
--   score                       = 无单位小数（0~100，越高越好）
--   scorecard.dimensions[*].score = 无单位小数（0~100，越高越好；风险维度存"风险规避分"）
--   scorecard.dimensions[*].weight = 无单位小数（0~1，同卡片内权重总和应 ≈ 1.0）
--
-- ─────────────────────────────────────────────────────────────────────
-- scorecard JSONB 契约（v1.0）
-- ─────────────────────────────────────────────────────────────────────
-- 策略输出的结构化评分卡。每个维度统一"得分越高越好"（risk 维度存风险规避分）。
-- 维度集合由 strategy 自由决定，但**必须至少包含一个 kind="risk" 的维度**。
-- final_score 由各维度加权计算，结果写入顶层 score 列（JSONB 内不冗余存 final_score）。
--
-- 形状:
-- {
--   "version":    "1.0",
--   "dimensions": {
--     "<dimension_key>": {
--       "score":   <0-100>,                -- 该维度得分，越高越好
--       "weight":  <0-1>,                  -- 该维度在 final_score 中的权重
--       "kind":    "reward" | "risk",     -- 维度性质（仅用于前端着色，不影响计算）
--       "details": { ... }                 -- 维度专属明细（任意结构）
--     }
--   }
-- }
--
-- 命名约定:
--   - dimension_key、details 内部字段使用 snake_case（与 DB / Python 约定一致）
--   - pulse-api repository 层负责递归 snake_case → camelCase 转换后再返回前端（§1.5 红线）
--
-- 示例（swing 赛道 macd 策略命中）:
-- {
--   "version": "1.0",
--   "dimensions": {
--     "trend":      { "score": 85, "weight": 0.30, "kind": "reward",
--                     "details": { "macd_signal": 0.92, "ma_alignment": "bull" } },
--     "momentum":   { "score": 72, "weight": 0.20, "kind": "reward",
--                     "details": { "rsi_14": 58, "volume_ratio": 1.8 } },
--     "volatility": { "score": 65, "weight": 0.20, "kind": "risk",
--                     "details": { "atr_pct_20d": 4.2 } },
--     "liquidity":  { "score": 85, "weight": 0.15, "kind": "risk",
--                     "details": { "turnover_5d": 3.5 } },
--     "st_flag":    { "score": 100, "weight": 0.15, "kind": "risk",
--                     "details": { "is_st": false } }
--   }
-- }
--
-- ─────────────────────────────────────────────────────────────────────
-- signals JSONB 契约（漏斗累积日志，可选）
-- ─────────────────────────────────────────────────────────────────────
-- 与 scorecard 互补：scorecard 是"打分结果"，signals 是"过关日志"。
-- 由 filter / strategy / risk 各阶段按 namespace 累积写入，便于调试与审计。
-- 半结构化：顶层 namespace 固定，内部字段自由。
--
-- 形状:
-- {
--   "filters":  { "<filter_name>": { "passed": true, ... } },
--   "strategy": { "name": "...", "raw_inputs": { ... } },
--   "risk":     { "<check_name>": { ... } }
-- }
--
-- 规范 §4.5.1：JSONB 是"逃生舱"，内部不加约束；若某子字段查询频繁应升列。
--
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE
    daily_picks (
        trade_date DATE             NOT NULL,
        track      VARCHAR(16)      NOT NULL,
        strategy   VARCHAR(32)      NOT NULL,
        ts_code    VARCHAR(16)      NOT NULL,
        score      DOUBLE PRECISION NOT NULL,
        scorecard  JSONB            NOT NULL,
        signals    JSONB,
        created_at TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        PRIMARY KEY (trade_date, track, strategy, ts_code),
        CONSTRAINT ck_daily_picks_score_range CHECK (score >= 0 AND score <= 100)
    );
