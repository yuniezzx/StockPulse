export type ExitReasonKey = string;

export interface ExitReasonMeta {
  key: ExitReasonKey;
  label: string;
  description: string;
  severity: "low" | "medium" | "high";
}

export const EXIT_REASON_META: Record<string, ExitReasonMeta> = {
  // TODO: 风控规则定义后填充
};
