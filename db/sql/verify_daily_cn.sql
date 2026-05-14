-- daily_cn 全量同步后验证脚本
-- 用法: 在你的 SQL 客户端连上 stockpulse 数据库, 直接整段执行,
-- 或按 -- ===== 标记的小节分别跑.

-- ===== 1. 总量统计 =====
-- 预期: ~400 万行, ~5300 stocks, ~730 days, 2023-01-03 ~ 今天
SELECT
    COUNT(*)                  AS total_rows,
    COUNT(DISTINCT ts_code)   AS stocks,
    COUNT(DISTINCT trade_date) AS days,
    MIN(trade_date)           AS first_day,
    MAX(trade_date)           AS last_day
FROM daily_cn;


-- ===== 2. 异常日: 股票数 < 平均 80% (可能拉数据失败) =====
-- 预期: 0 行
WITH daily_counts AS (
    SELECT trade_date, COUNT(*) AS cnt
    FROM daily_cn
    GROUP BY trade_date
),
stats AS (
    SELECT AVG(cnt) AS avg_cnt FROM daily_counts
)
SELECT trade_date, cnt
FROM daily_counts, stats
WHERE cnt < stats.avg_cnt * 0.8
ORDER BY trade_date;


-- ===== 3. 缺失的交易日: trade_cal 中是交易日, 但 daily_cn 没数据 =====
-- 预期: 0 行
SELECT cal_date
FROM trade_cal_cn
WHERE exchange = 'SSE'
  AND is_open = 1
  AND cal_date BETWEEN '2023-01-01' AND CURRENT_DATE
  AND cal_date NOT IN (SELECT DISTINCT trade_date FROM daily_cn)
ORDER BY cal_date;


-- ===== 4. 每天股票数 (整体趋势, 应平滑递增) =====
-- 预期: 2023 ~5100, 2026 ~5500; 无突降
SELECT trade_date, COUNT(*) AS stock_count
FROM daily_cn
GROUP BY trade_date
ORDER BY trade_date;


-- ===== 5. 主流股票交易日数 =====
-- 预期: 每只 ~730 天 (老股票应该一致)
SELECT
    ts_code,
    COUNT(*) AS days,
    MIN(trade_date) AS first_day,
    MAX(trade_date) AS last_day
FROM daily_cn
WHERE ts_code IN (
    '000001.SZ',  -- 平安银行
    '600519.SH',  -- 茅台
    '000858.SZ',  -- 五粮液
    '600036.SH',  -- 招商银行
    '000333.SZ',  -- 美的
    '300750.SZ',  -- 宁德时代
    '601318.SH',  -- 中国平安
    '600276.SH',  -- 恒瑞医药
    '002594.SZ',  -- 比亚迪
    '000625.SZ'   -- 长安汽车
)
GROUP BY ts_code
ORDER BY ts_code;


-- ===== 6. 单位准确性: 平安银行最近 5 天 =====
-- 核对: amount / vol 应该 ≈ close (均价≈收盘价, 单位换算才对)
-- 对照: 东方财富 https://quote.eastmoney.com/sz000001.html
-- 预期范围: close ~11-15 元, vol 千万到亿股, amount 亿元级
SELECT
    trade_date,
    open, high, low, close, pre_close,
    change, pct_chg,
    vol,
    amount,
    ROUND((amount / NULLIF(vol, 0))::numeric, 2) AS avg_price
FROM daily_cn
WHERE ts_code = '000001.SZ'
ORDER BY trade_date DESC
LIMIT 5;


-- ===== 7. 单位准确性: 茅台最近 5 天 =====
-- 预期: close ~1500-1800 元, vol 几百万股, amount 几十亿元
SELECT
    trade_date,
    close, vol, amount,
    ROUND((amount / NULLIF(vol, 0))::numeric, 2) AS avg_price,
    pct_chg
FROM daily_cn
WHERE ts_code = '600519.SH'
ORDER BY trade_date DESC
LIMIT 5;


-- ===== 8. 异常涨跌幅 (>25%) =====
-- A 股涨跌停 10%/20%, 超出可能是 ST/IPO 首日/复牌, 应该不多
SELECT COUNT(*) AS abnormal_pct_chg_count
FROM daily_cn
WHERE ABS(pct_chg) > 25;

-- 具体看一下哪些 (抽样 10 条)
SELECT ts_code, trade_date, pct_chg, close, pre_close
FROM daily_cn
WHERE ABS(pct_chg) > 25
ORDER BY ABS(pct_chg) DESC
LIMIT 10;


-- ===== 9. 异常价格: <= 0 =====
-- 预期: 0 行
SELECT COUNT(*) AS bad_price_count
FROM daily_cn
WHERE close <= 0 OR open <= 0 OR high <= 0 OR low <= 0;


-- ===== 10. 高低价逻辑检查 (low > high 等异常) =====
-- 预期: 0 行
SELECT COUNT(*) AS price_logic_violations
FROM daily_cn
WHERE low > high
   OR open > high
   OR open < low
   OR close > high
   OR close < low;


-- ===== 11. 成交量/成交额为 0 的行 (停牌日, 可有少量) =====
SELECT COUNT(*) AS zero_vol_count
FROM daily_cn
WHERE vol = 0 OR vol IS NULL;


-- ===== 12. 表大小和索引大小 =====
-- 预期: table ~400-500 MB, indexes ~150-250 MB
SELECT
    pg_size_pretty(pg_total_relation_size('daily_cn')) AS total_size,
    pg_size_pretty(pg_relation_size('daily_cn'))       AS table_size,
    pg_size_pretty(pg_indexes_size('daily_cn'))        AS indexes_size;


-- ===== 13. 查询性能 (主键查询, 应该 < 50ms) =====
EXPLAIN ANALYZE
SELECT * FROM daily_cn
WHERE ts_code = '000001.SZ'
ORDER BY trade_date DESC
LIMIT 30;


-- ===== 14. 查询性能 (按日期查询, 应该 < 100ms) =====
EXPLAIN ANALYZE
SELECT * FROM daily_cn
WHERE trade_date = (SELECT MAX(trade_date) FROM daily_cn)
LIMIT 100;
