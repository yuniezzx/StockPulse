-- 验证 daily_basic_cn 表数据是否正常
-- 用法: psql -U max -d stockpulse -f pulse-core/sql/verify_daily_basic_cn.sql

\echo '=== Overview ==='
SELECT COUNT(*) AS total_rows,
       COUNT(DISTINCT ts_code) AS unique_stocks,
       MIN(trade_date) AS first_date,
       MAX(trade_date) AS last_date
FROM daily_basic_cn;

\echo ''
\echo '=== Row count by trade_date ==='
SELECT trade_date, COUNT(*) AS row_count
FROM daily_basic_cn
GROUP BY trade_date
ORDER BY trade_date DESC
LIMIT 10;

\echo ''
\echo '=== Valuation distribution on latest trade_date ==='
SELECT
  ROUND(AVG(pe)::numeric, 2)             AS avg_pe,
  ROUND(AVG(pb)::numeric, 2)             AS avg_pb,
  ROUND(AVG(turnover_rate)::numeric, 2)  AS avg_turnover_pct,
  COUNT(*) FILTER (WHERE pe IS NULL)     AS null_pe_count
FROM daily_basic_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM daily_basic_cn);

\echo ''
\echo '=== Market cap unit check (亿元单位) ==='
SELECT ts_code,
       ROUND((total_mv / 1e8)::numeric, 2) AS total_mv_yi,
       ROUND((circ_mv  / 1e8)::numeric, 2) AS circ_mv_yi,
       ROUND((total_share / 1e8)::numeric, 2) AS total_share_yi
FROM daily_basic_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM daily_basic_cn)
  AND ts_code IN ('600519.SH', '601398.SH', '000001.SZ')
ORDER BY ts_code;

\echo ''
\echo '=== Sample rows on latest trade_date ==='
SELECT ts_code, trade_date, close, turnover_rate, pe, pb, circ_mv
FROM daily_basic_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM daily_basic_cn)
ORDER BY ts_code
LIMIT 5;
