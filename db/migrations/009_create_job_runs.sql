-- 009: create job_runs table
-- pulse-core scheduler/worker 任务运行记录。
--
-- 用途:
--   1. APScheduler 到点时 INSERT 一条 pending 行（trigger_source='cron'）
--   2. pulse-api 收到用户手动触发时 INSERT 一条 pending 行（trigger_source='manual'）
--   3. worker 轮询 pending 行 → 更新 running → success/failed/partial/skipped
--
-- 写权限例外（见 architecture.md §4.2 例外条款）:
--   pulse-api 仅允许 INSERT status='pending' 的行（用户手动触发入口）
--   所有 UPDATE 只能由 pulse-core worker
--
-- 字段说明:
--   job_name:       registry 注册的 job key（如 evening_ingestion / sync_daily_cn）
--   trigger_source: cron=定时触发, manual=用户手动, dependency=依赖链触发
--   scheduled_at:   计划运行时间（cron 触发时刻 / 手动触发的 NOW()）
--   started_at:     worker 实际开始执行的时刻，pending 状态下为 NULL
--   finished_at:    结束时刻，pending/running 状态下为 NULL
--   status:         pending → running → success | failed | partial | skipped
--   rows_affected:  成功时 worker 写入的行数（可空，部分 job 无明确行数）
--   error_message:  失败时的异常信息（截断到合理长度由 worker 控制）
--   details:        JSONB，sub-step 状态、上下文，如 ingestion 5 子任务的各自结果
--
-- 主键: id（单列，查询永远按 job_name+started_at 或 status+scheduled_at）
-- 业务索引:
--   pending 部分索引: worker 取任务的高频查询（SELECT ... FOR UPDATE SKIP LOCKED）
--   (job_name, started_at DESC): pulse-api 查"上次该 job 跑得怎样"
--   cron 去重 partial unique: 防止 daemon 重启时 APScheduler misfire 重复 enqueue
--                             （仅 trigger_source='cron'；manual/dependency 允许同时刻多次触发）
CREATE TABLE
    job_runs (
        id             BIGSERIAL        PRIMARY KEY,
        job_name       VARCHAR(64)      NOT NULL,
        trigger_source VARCHAR(16)      NOT NULL
            CHECK (trigger_source IN ('cron', 'manual', 'dependency')),
        scheduled_at   TIMESTAMPTZ      NOT NULL,
        started_at     TIMESTAMPTZ,
        finished_at    TIMESTAMPTZ,
        status         VARCHAR(16)      NOT NULL
            CHECK (status IN ('pending', 'running', 'success', 'failed', 'partial', 'skipped')),
        rows_affected  BIGINT,
        error_message  TEXT,
        details        JSONB,
        created_at     TIMESTAMPTZ      NOT NULL DEFAULT NOW()
    );

CREATE INDEX idx_job_runs_pending
    ON job_runs (scheduled_at)
    WHERE status = 'pending';

CREATE INDEX idx_job_runs_name_started
    ON job_runs (job_name, started_at DESC);

CREATE UNIQUE INDEX idx_job_runs_cron_dedup
    ON job_runs (job_name, scheduled_at)
    WHERE trigger_source = 'cron';
