-- 验证 stocks_cn 表数据是否正常
-- 用法: psql -U max -d stockpulse -f pulse-core/sql/verify_stocks_cn.sql

\echo '=== Total rows ==='
SELECT COUNT(*) AS total_rows
FROM stocks_cn;

\echo ''
\echo '=== Row count by exchange ==='
SELECT exchange, COUNT(*) AS rows
FROM stocks_cn
GROUP BY exchange
ORDER BY exchange;

\echo ''
\echo '=== Row count by list_status ==='
SELECT list_status, COUNT(*) AS rows
FROM stocks_cn
GROUP BY list_status
ORDER BY list_status;

\echo ''
\echo '=== Row count by market ==='
SELECT COALESCE(market, '(null)') AS market, COUNT(*) AS rows
FROM stocks_cn
GROUP BY COALESCE(market, '(null)')
ORDER BY rows DESC, market;

\echo ''
\echo '=== Sample stocks ==='
SELECT ts_code, symbol, name, market, exchange, list_status, list_date
FROM stocks_cn
WHERE ts_code IN ('000001.SZ', '000002.SZ', '600000.SH', '600519.SH', '688981.SH')
ORDER BY ts_code;
