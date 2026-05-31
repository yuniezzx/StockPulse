/**
 * Track（赛道）元数据：超短 / 波段 / 中线三档。
 *
 * 赛道是顶层分类，对应不同持仓周期与策略偏好。
 * key 与 pulse-core 的 screener/tracks/{key}.yaml 完全一致（AGENTS.md §1 跨语言契约）。
 */
export type TrackKey = "scalp" | "swing" | "position";

export interface TrackMeta {
  key: TrackKey;
  label: string;        // 中文名
  description: string;  // 一句话说明
  color: string;        // tailwind color
}

export const TRACK_META: Record<TrackKey, TrackMeta> = {
  scalp: {
    key: "scalp",
    label: "超短",
    description: "1-3 天持仓，涨停/突破驱动。",
    color: "bg-red-500",
  },
  swing: {
    key: "swing",
    label: "波段",
    description: "1-3 周持仓，回踩/形态驱动。",
    color: "bg-amber-500",
  },
  position: {
    key: "position",
    label: "中线",
    description: "1-3 月持仓，MACD/基本面驱动。",
    color: "bg-blue-500",
  },
};

export const TRACK_KEYS = ["scalp", "swing", "position"] as const;
