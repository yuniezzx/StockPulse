-- 验证 trade_cal_cn 表数据是否正常
-- 用法: psql -U max -d stockpulse -f pulse-core/sql/verify_trade_cal_cn.sql

\echo '=== Row count by exchange ==='
SELECT exchange, COUNT(*) AS rows, MIN(cal_date) AS earliest, MAX(cal_date) AS latest
FROM trade_cal_cn
GROUP BY exchange
ORDER BY exchange;

\echo ''
\echo '=== Open days by year (sanity check: 240-250 trading days/year) ==='
SELECT exchange,
       EXTRACT(YEAR FROM cal_date)::int AS year,
       SUM(is_open) AS open_days,
       COUNT(*) AS total_days
FROM trade_cal_cn
GROUP BY exchange, year
ORDER BY exchange, year;

\echo ''
\echo '=== Most recent 5 trading days (SSE) ==='
SELECT cal_date, is_open, pretrade_date
FROM trade_cal_cn
WHERE exchange = 'SSE' AND is_open = 1
ORDER BY cal_date DESC
LIMIT 5;
