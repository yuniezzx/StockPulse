-- 验证 moneyflow_cn 表数据是否正常
-- 用法: psql -U max -d stockpulse -f pulse-core/sql/verify_moneyflow_cn.sql

\echo '=== Overview ==='
SELECT COUNT(*) AS total_rows,
       COUNT(DISTINCT ts_code) AS unique_stocks,
       MIN(trade_date) AS first_date,
       MAX(trade_date) AS last_date
FROM moneyflow_cn;

\echo ''
\echo '=== Row count by trade_date ==='
SELECT trade_date, COUNT(*) AS row_count
FROM moneyflow_cn
GROUP BY trade_date
ORDER BY trade_date DESC
LIMIT 10;

\echo ''
\echo '=== Net money flow distribution on latest trade_date (亿元) ==='
SELECT
  ROUND((MIN(net_mf_amount) / 1e8)::numeric, 2) AS min_net_yi,
  ROUND((MAX(net_mf_amount) / 1e8)::numeric, 2) AS max_net_yi,
  ROUND((AVG(net_mf_amount) / 1e8)::numeric, 4) AS avg_net_yi,
  COUNT(*) FILTER (WHERE net_mf_amount > 0)     AS positive_count,
  COUNT(*) FILTER (WHERE net_mf_amount < 0)     AS negative_count
FROM moneyflow_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM moneyflow_cn);

\echo ''
\echo '=== Top 5 net inflow on latest trade_date ==='
SELECT ts_code, trade_date,
       ROUND((net_mf_amount / 1e8)::numeric, 2) AS net_yi,
       ROUND(((buy_lg_amount + buy_elg_amount) / 1e8)::numeric, 2) AS main_buy_yi,
       ROUND(((sell_lg_amount + sell_elg_amount) / 1e8)::numeric, 2) AS main_sell_yi
FROM moneyflow_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM moneyflow_cn)
ORDER BY net_mf_amount DESC
LIMIT 5;

\echo ''
\echo '=== Unit conversion sanity check (vol 单位=股；amount 单位=元) ==='
SELECT ts_code,
       buy_lg_vol,
       buy_lg_amount,
       net_mf_vol,
       net_mf_amount
FROM moneyflow_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM moneyflow_cn)
  AND ts_code IN ('600519.SH', '601398.SH', '000001.SZ')
ORDER BY ts_code;
