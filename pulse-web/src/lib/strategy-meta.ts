/**
 * Strategy 元数据：策略 key -> 展示用 label/description/color/默认 track。
 *
 * 当前为空，新增策略时按 AGENTS.md §4「新增 checklist · 新选股策略」流程：
 *   1. pulse-core/screener/strategies/{key}.py（类 `{Key}Strategy`，`name = "{key}"`）
 *   2. tracks/{track}.yaml 注册
 *   3. 在本文件登记元数据（key 三层完全一致）
 */
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
  // 示例：breakout: { key: "breakout", label: "突破", description: "...", color: "bg-blue-500", track: "swing" },
};
