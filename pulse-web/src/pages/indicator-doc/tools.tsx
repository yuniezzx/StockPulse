import { IndicatorSectionPage } from "@/components/indicator-doc/indicator-section-page";

const content = {
  qfq: (
    <div className="space-y-4 text-sm">
      <p>
        前复权（qfq）将历史价格按最新除权除息口径回溯调整，使得不同时间点的价格在同一坐标系下可比。
        所有数值型指标（MA / MACD / RSI 等）均基于 qfq 口径计算。
      </p>

      <div>
        <h3 className="mb-1 font-medium">公式</h3>
        <pre className="bg-muted overflow-x-auto rounded p-3 text-xs">
{`ratio       = adj_factor / latest_adj_factor    ∈ (0, 1]
{open,high,low,close}_qfq = price * ratio
vol_qfq     = vol / ratio                       (量价反向)`}
        </pre>
      </div>

      <div>
        <h3 className="mb-1 font-medium">函数签名</h3>
        <pre className="bg-muted overflow-x-auto rounded p-3 text-xs">
{`apply_qfq(
    daily_df: pd.DataFrame,
    adj_df: pd.DataFrame,
    latest_adj: dict[str, float] | None = None,
) -> pd.DataFrame`}
        </pre>
        <p className="text-muted-foreground mt-1 text-xs">
          位于 <code>pulse_core/indicators/adjust.py</code>。
        </p>
      </div>

      <div>
        <h3 className="mb-1 font-medium">参数说明</h3>
        <ul className="ml-4 list-disc space-y-1">
          <li>
            <code>daily_df</code> — 含 <code>ts_code / trade_date / open / high / low / close / vol</code>
          </li>
          <li>
            <code>adj_df</code> — 含 <code>ts_code / trade_date / adj_factor</code>
          </li>
          <li>
            <code>latest_adj</code>（可选） — <code>{`{ts_code: 最新 adj_factor}`}</code>。
            生产环境由 T10 从 DB 查 <code>SELECT DISTINCT ON (ts_code)</code> 传入；
            不传则 fallback 到 <code>adj_df</code> 内最后一行（要求 adj_df 必须是全历史）。
          </li>
        </ul>
      </div>

      <div>
        <h3 className="mb-1 font-medium">输出列</h3>
        <p>
          在原始 7 列基础上新增 5 列：<code>open_qfq / high_qfq / low_qfq / close_qfq / vol_qfq</code>。
          原始列保留，便于涨跌停判定等需要原始价的场景。
        </p>
      </div>

      <div>
        <h3 className="mb-1 font-medium">注意事项</h3>
        <ul className="ml-4 list-disc space-y-1">
          <li>
            <strong>qfq 漂移</strong>：每次新除权事件触发后，历史所有价格按新基准重算，与 Tushare <code>pro_bar(adj=&apos;qfq&apos;)</code> 行为一致。
            策略的布尔判定（金叉/新高等）不受漂移影响。
          </li>
          <li>
            <strong>全量重算</strong>：indicators 走 <code>mode=&quot;full_rebuild&quot;</code>，每晚 ingestion 后整批刷新 4 张指标表。
          </li>
          <li>
            <strong>涨跌停判定例外</strong>：<code>is_limit_up / is_limit_down</code> 使用 <em>原始 close</em> 比对 <code>stk_limit_cn</code>，不走 qfq。
          </li>
        </ul>
      </div>
    </div>
  ),
};

export default function IndicatorToolsPage() {
  return <IndicatorSectionPage slug="tools" content={content} />;
}
