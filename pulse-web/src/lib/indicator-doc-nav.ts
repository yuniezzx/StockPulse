/**
 * Indicator-doc navigation data — single source of truth for section slugs and indicator anchors.
 * The anchor validation script (scripts/check-indicator-anchors.ts) verifies that every anchor
 * listed here has a corresponding MDX file with a matching {#anchor} heading ID.
 */
export type DocNavItem = {
  anchor: string;
  title: string;
  hint?: string;
};

const indicatorDocNavData = [
  {
    slug: "tools",
    title: "工具 Tools",
    items: [
      { anchor: "qfq", title: "前复权 (qfq)", hint: "apply_qfq" },
    ],
  },
  {
    slug: "trend",
    title: "趋势 Trend",
    items: [
      { anchor: "ma", title: "MA 均线", hint: "MA5/10/20/60" },
      { anchor: "ema", title: "EMA 指数均线", hint: "EMA12/26" },
      { anchor: "macd", title: "MACD", hint: "DIF/DEA/Hist" },
    ],
  },
  {
    slug: "momentum",
    title: "动量 Momentum",
    items: [
      { anchor: "rsi", title: "RSI", hint: "RSI6/12/24" },
      { anchor: "atr", title: "ATR 真实波幅", hint: "ATR14" },
      { anchor: "pct-chg", title: "N 日涨跌幅", hint: "5d/20d" },
      { anchor: "candle-shape", title: "K 线形态", hint: "跳空/实体" },
      { anchor: "limit-up-down", title: "涨停 / 跌停" },
      { anchor: "new-high-low", title: "60 日新高/新低" },
    ],
  },
  {
    slug: "volume",
    title: "量能 Volume",
    items: [
      { anchor: "turnover", title: "换手率与均值" },
      { anchor: "volume-ratio", title: "量比" },
      { anchor: "pe-pb-quantile", title: "PE/PB 分位" },
    ],
  },
  {
    slug: "moneyflow",
    title: "资金 Moneyflow",
    items: [
      { anchor: "main-net", title: "主力净额" },
      { anchor: "retail-net", title: "散户净额" },
    ],
  },
] as const;

export type DocNavAnchor = (typeof indicatorDocNavData)[number]["items"][number]["anchor"];

export type DocNavSection = {
  slug: (typeof indicatorDocNavData)[number]["slug"];
  title: string;
  items: readonly DocNavItem[];
};

export const indicatorDocNav = indicatorDocNavData satisfies readonly DocNavSection[];

export function getSectionBySlug(slug: DocNavSection["slug"]): DocNavSection | undefined {
  return indicatorDocNav.find((s) => s.slug === slug) as DocNavSection | undefined;
}

export function getAllAnchors(): DocNavAnchor[] {
  return indicatorDocNav.flatMap((s) => s.items.map((i) => i.anchor)) as DocNavAnchor[];
}
