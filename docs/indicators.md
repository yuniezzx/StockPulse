# StockPulse 指标系统文档

> **本文是 StockPulse 指标系统的唯一来源。**
> 命名总规则见 [naming-conventions.md](naming-conventions.md)；架构总览见 [architecture.md](architecture.md) §5.2/§6。

---

## 1. 指标层职责

**物理位置**：`pulse-core/pulse_core/indicators/`

按 domain 切分为 5 个模块：

| 文件 | Domain | 覆盖内容 |
|---|---|---|
| `adjust.py` | adjust | 前复权价格修正 |
| `trend.py` | trend | 均线、MACD 等趋势类指标 |
| `momentum.py` | momentum | RSI、ATR、涨跌幅、K 线形态 |
| `volume.py` | volume | 量能、换手率、估值分位 |
| `moneyflow.py` | moneyflow | 主力资金、散户资金净流入 |

**输出表**：计算结果写入 4 张派生表（见 database.md §6 圈 2）：
`daily_trend_indicators_cn` / `daily_momentum_indicators_cn` / `daily_volume_indicators_cn` / `daily_moneyflow_indicators_cn`

**消费方**：
- screener（选股）：读取指标列做策略过滤
- analysis domain（个股分析页）：读取指标列做图表展示

**MDX 文档位置**：`pulse-web/src/content/indicator-doc/{domain}/{anchor}.mdx`

---

## 2. 指标列命名清单

- 指标列：小写简称
  - 均线（trend）：`ma5` / `ma10` / `ma20` / `ma60`（**指标名 + 周期数字直接拼接**，不要 `ma_20`）
  - 指数均线（trend）：`ema12` / `ema26`
  - MACD（trend）：`dif` / `dea` / `hist`
  - RSI（momentum）：`rsi6` / `rsi12` / `rsi24`
  - ATR（momentum）：`atr14`
  - 累计涨跌幅（momentum）：`pct_chg_5d` / `pct_chg_20d`
  - K 线形态（momentum）：`gap_pct` / `body_pct`（小数，0.05 = 5%）
  - 量能（volume）：`vol_ma5` / `vol_ma10` / `vol_ratio_5`
  - 换手（volume）：`turnover_rate_ma5` / `turnover_rate_ratio_5`
- 估值分位（volume）：`pe_ttm_pct_60` / `pb_pct_60`
- 主力资金（moneyflow）：`main_net_amount` / `main_net_ratio` / `main_net_amount_ma5`
- 散户资金（moneyflow）：`retail_net_amount`
- 布尔派生列：`is_xxx` 前缀，warmup 期所有依赖列任一为 null 时本列也为 null
  - 多头排列：`is_ma_bull_arrangement` / `is_rsi_bull_arrangement`
  - 趋势信号：`is_macd_golden_cross`
  - 价格触界：`is_limit_up` / `is_limit_down` / `is_new_high_60d` / `is_new_low_60d`

---

## 3. 指标文档（MDX）格式约定

**范围**：`pulse-web/src/content/indicator-doc/{domain}/{anchor}.mdx`（domain ∈ `trend` / `momentum` / `volume` / `moneyflow` / `tools`）。

### 3.1 文件位置与命名

- 路径：`pulse-web/src/content/indicator-doc/{domain}/{anchor}.mdx`
- `{anchor}` 必须与 `pulse-web/src/lib/indicator-doc-nav.ts` 中注册的 `anchor` 字段**完全一致**
- 校验脚本：`pulse-web/scripts/check-indicator-anchors.ts`（已接入 `pnpm typecheck`）

### 3.2 强制 7 节结构

每篇指标文档**必须**按以下顺序与节标题书写，缺一不可、不可重排：

1. `## {中文标题}` — 一级标题（见 §3.3）
2. 紧接一段话简介：指标定位 + 主要用途 + 单位
3. `### 公式` — KaTeX 公式块，用 `$$ ... $$` 包裹；多步骤公式分多个块
4. `### 例子` — 用一段表格演示一次计算；warmup 期用 null 标记
5. `### 函数签名` — Python 代码块写 `compute_xxx(df: pd.DataFrame) -> pd.DataFrame`，下一行注明 `位于 pulse_core/indicators/{domain}.py`
6. `### 参数说明` — 用 `- df — 含 {输入列清单}，已按 ts_code + trade_date 排序` 格式逐项列出
7. `### 输出列` — 三列表格 `| 字段 | 窗口 | 含义 |`，每个新增列一行
8. `### 注意事项` — bullet 列表，覆盖 warmup 行数、除零/NaN 处理、阈值类信号归属（`screener/` 或 `risk/`）、多股隔离

样板请参考：`pulse-web/src/content/indicator-doc/momentum/atr.mdx`、`momentum/rsi.mdx`、`trend/ma.mdx`。

### 3.3 标题格式（重要）

- 一级标题**只用** markdown `## 中文标题`
- **禁止**用 `<h2 id="...">中文标题</h2>` 的 HTML 占位写法
- 锚点 ID 由 `rehype-slug` 从标题文本自动生成；nav 的 `anchor` 字段在 URL hash 中工作
- placeholder（新建未填充时）也用 `## 待补充：{中文标题}`，不要混用 HTML

### 3.4 MDX 转义陷阱

- `<` 后紧跟字母/数字（如 `<5万`）会被 MDX 当 JSX 标签解析，**必须**写成 HTML 实体 `&lt;5万`
- `>` 在大多数位置安全，不需要转义；但行首作为引用块要小心
- 反引号 `` ` `` 在表格单元格内正常使用，无需转义
- 中文括号 `（）` 不触发 MDX 解析，与英文括号 `()` 在 KaTeX 外可混用

### 3.5 KaTeX 公式约定

- 字段名用 `\text{xxx}`，下划线必须转义为 `\_`：`\text{main\_net\_amount}`
- 单步公式独占一个 `$$ ... $$` 块
- 多步推导拆多块，便于阅读和换行
- 行内变量引用用 `$ ... $`：`这里直接使用 $\text{avg\_gain}$`
- 求和符号写法：`\sum_{i=0}^{n-1}`；均值写法：`\frac{1}{n}\sum_{i=0}^{n-1} x_{t-i}`

---

## 修订记录

| 版本 | 日期 | 说明 |
|---|---|---|
| v1.0 | 2026-06-01 | 从 naming holdings 块 E + 块 A 抽出独立成文 |
