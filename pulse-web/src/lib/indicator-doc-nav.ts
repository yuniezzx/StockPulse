export type DocNavItem = {
  anchor: string;
  title: string;
  hint?: string;
};

export type DocNavSection = {
  slug: "tools" | "trend" | "momentum" | "volume" | "moneyflow";
  title: string;
  items: DocNavItem[];
};

export const indicatorDocNav: DocNavSection[] = [
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
      { anchor: "is-ma-bull-arrangement", title: "均线多头排列" },
    ],
  },
  {
    slug: "momentum",
    title: "动量 Momentum",
    items: [
      { anchor: "rsi", title: "RSI", hint: "RSI6/12/24" },
      { anchor: "pct-chg", title: "N 日涨跌幅", hint: "5d/20d" },
      { anchor: "is-limit-up", title: "涨停 / 跌停" },
      { anchor: "is-new-high-60d", title: "60 日新高/新低" },
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
];
