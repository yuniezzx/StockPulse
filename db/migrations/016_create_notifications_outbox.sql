-- 016: create notifications_outbox table
-- 通知出箱模式的核心表（架构红线 ⑥）：
--   pulse-core 写 → pulse-api 在调度时刻扫描 → 聚合 → 发送 → 标 sent
--
-- 设计要点：
--   - 同事务原子写入：选股 / 虚拟仓 / 通知三件事在 screener runner
--     的单事务内一起完成，杜绝"选股写了但通知漏了"的不一致
--   - 早报节奏 = 聚合：scheduled_at = 次日 07:00；多个事件合并成一封早报
--   - 运维告警节奏 = 即时：scheduled_at = NOW()；失败发送时再写一条触发即时通道
--   - status 状态机：pending → sent / failed / cancelled（不会回退）
--   - user_id：系统初期单用户（固定 1），列保留为多用户预留
--
-- payload 结构（按 event_type）：
--   screener_picks: { trade_date, run_id, tracks: [{ track, picks: [{ ts_code, strategy, final_score, ... }] }] }
--   job_failed:     { job_name, run_id, error_message, scheduled_at }
--   notifier_failed:{ outbox_id, error_message }
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE
    notifications_outbox (
        id            BIGSERIAL    PRIMARY KEY,
        user_id       BIGINT       NOT NULL,
        event_type    VARCHAR(32)  NOT NULL,
        payload       JSONB        NOT NULL,
        scheduled_at  TIMESTAMPTZ  NOT NULL,
        status        VARCHAR(16)  NOT NULL DEFAULT 'pending',
        sent_at       TIMESTAMPTZ,
        error_message TEXT,
        created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        CONSTRAINT ck_outbox_status CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
        CONSTRAINT ck_outbox_sent_at CHECK (
            (status = 'sent' AND sent_at IS NOT NULL)
            OR (status <> 'sent' AND sent_at IS NULL)
        )
    );

-- 主索引：pulse-api 扫描器扫待发送事件用
-- 部分索引：只索引 pending 行（活跃集小，已发送的占绝大多数但不参与扫描）
CREATE INDEX ix_outbox_pending_sched
    ON notifications_outbox (scheduled_at)
    WHERE status = 'pending';

-- 辅助索引：按用户查历史通知（pulse-api 消息中心用）
CREATE INDEX ix_outbox_user_created
    ON notifications_outbox (user_id, created_at DESC);
