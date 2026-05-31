-- 验证 adj_factor_cn 表数据是否正常
-- 用法: psql -U max -d stockpulse -f pulse-core/sql/verify_adj_factor_cn.sql

\echo '=== Overview ==='
SELECT COUNT(*) AS total_rows,
       COUNT(DISTINCT ts_code) AS unique_stocks,
       MIN(trade_date) AS first_date,
       MAX(trade_date) AS last_date
FROM adj_factor_cn;

\echo ''
\echo '=== Row count by trade_date (sanity check: ~5500/day) ==='
SELECT trade_date, COUNT(*) AS row_count
FROM adj_factor_cn
GROUP BY trade_date
ORDER BY trade_date DESC
LIMIT 10;

\echo ''
\echo '=== Latest trade_date adj_factor distribution ==='
SELECT MIN(adj_factor) AS min_factor,
       MAX(adj_factor) AS max_factor,
       AVG(adj_factor) AS avg_factor
FROM adj_factor_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM adj_factor_cn);

\echo ''
\echo '=== Sample rows on latest trade_date ==='
SELECT ts_code, trade_date, adj_factor
FROM adj_factor_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM adj_factor_cn)
ORDER BY ts_code
LIMIT 5;
