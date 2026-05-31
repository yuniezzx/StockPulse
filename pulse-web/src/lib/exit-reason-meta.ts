/**
 * Exit reason 元数据：风控触发原因的展示信息。
 *
 * 由 pulse-core/risk 写入卖出信号时携带的 exit_reason key 解析为 UI 友好展示。
 * 当前为空，风控规则定义后按 key 填充（与 pulse-core 完全对齐）。
 */
export type ExitReasonKey = string;

export interface ExitReasonMeta {
  key: ExitReasonKey;
  label: string;
  description: string;
  severity: "low" | "medium" | "high";
}

export const EXIT_REASON_META: Record<string, ExitReasonMeta> = {
  // 待 pulse-core/risk 定义规则后按 key 填充
};
