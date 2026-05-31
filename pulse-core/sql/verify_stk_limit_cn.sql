-- 验证 stk_limit_cn 表数据是否正常
-- 用法: psql -U max -d stockpulse -f pulse-core/sql/verify_stk_limit_cn.sql

\echo '=== Overview ==='
SELECT COUNT(*) AS total_rows,
       COUNT(DISTINCT ts_code) AS unique_stocks,
       MIN(trade_date) AS first_date,
       MAX(trade_date) AS last_date
FROM stk_limit_cn;

\echo ''
\echo '=== Row count by trade_date (sanity check: ~5500/day) ==='
SELECT trade_date, COUNT(*) AS row_count
FROM stk_limit_cn
GROUP BY trade_date
ORDER BY trade_date DESC
LIMIT 10;

\echo ''
\echo '=== Latest trade_date limit distribution ==='
SELECT MIN(up_limit) AS min_up, MAX(up_limit) AS max_up,
       MIN(down_limit) AS min_down, MAX(down_limit) AS max_down
FROM stk_limit_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM stk_limit_cn);

\echo ''
\echo '=== Sample rows on latest trade_date ==='
SELECT ts_code, trade_date, up_limit, down_limit,
       ROUND((up_limit / down_limit - 1)::numeric * 100 / 2, 1) AS pct_band_pct
FROM stk_limit_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM stk_limit_cn)
ORDER BY ts_code
LIMIT 5;
