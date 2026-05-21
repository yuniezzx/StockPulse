import type { TrackKey } from "./track-meta";

export type StrategyKey = string; // 后续可窄化为 union literal

export interface StrategyMeta {
  key: StrategyKey;
  label: string;        // 中文显示名
  description: string;  // 一句话说明
  color: string;        // tailwind color class，如 "bg-blue-500"
  track: TrackKey;      // 默认归属赛道
}

export const STRATEGY_META: Record<string, StrategyMeta> = {
  // TODO: 在新增策略时按 naming-conventions §2.3 同步登记
  // 例：
  // breakout: { key: "breakout", label: "突破", description: "...", color: "bg-blue-500", track: "swing" },
};
