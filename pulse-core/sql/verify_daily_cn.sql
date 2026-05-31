-- 验证 daily_cn 表数据是否正常
-- 用法: psql -U max -d stockpulse -f pulse-core/sql/verify_daily_cn.sql

\echo '=== Total rows ==='
SELECT COUNT(*) AS total_rows
FROM daily_cn;

\echo ''
\echo '=== Trade date coverage ==='
SELECT MIN(trade_date) AS earliest,
       MAX(trade_date) AS latest,
       COUNT(DISTINCT trade_date) AS trading_days
FROM daily_cn;

\echo ''
\echo '=== Row count by trade_date (sanity check: ~5400/day) ==='
SELECT trade_date, COUNT(*) AS rows
FROM daily_cn
GROUP BY trade_date
ORDER BY trade_date;

\echo ''
\echo '=== Sample rows on latest trade_date (vol 千万~亿 / amount 亿~百亿 验证单位转换) ==='
SELECT ts_code, trade_date, close, vol, amount
FROM daily_cn
WHERE ts_code IN ('000001.SZ', '600000.SH', '600519.SH', '688981.SH', '000002.SZ')
  AND trade_date = (SELECT MAX(trade_date) FROM daily_cn)
ORDER BY ts_code;
