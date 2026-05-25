import type { ReactNode } from "react";

export function ParamTable({ children }: { children: ReactNode }) {
  return (
    <div data-param-table className="my-6 overflow-x-auto">
      <table className="w-full text-[14px] border-collapse">
        <thead>
          <tr>
            <th className="border-b border-border px-3 py-2 text-left font-medium w-32">参数</th>
            <th className="border-b border-border px-3 py-2 text-left font-medium w-32">类型</th>
            <th className="border-b border-border px-3 py-2 text-left font-medium w-16">必填</th>
            <th className="border-b border-border px-3 py-2 text-left font-medium">说明</th>
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function ParamRow({
  name,
  type,
  required,
  description,
}: {
  name: string;
  type: string;
  required?: boolean;
  description: ReactNode;
}) {
  return (
    <tr>
      <td className="border-b border-border/60 px-3 py-2 align-top font-mono text-[13px]">{name}</td>
      <td className="border-b border-border/60 px-3 py-2 align-top font-mono text-[13px] text-muted-foreground">{type}</td>
      <td className="border-b border-border/60 px-3 py-2 align-top text-center">{required ? "✓" : ""}</td>
      <td className="border-b border-border/60 px-3 py-2 align-top text-[13px]">{description}</td>
    </tr>
  );
}
