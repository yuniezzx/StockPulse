import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type CalloutType = "note" | "warning" | "tip";

const calloutVariants = cva(
  "border-l-[3px] pl-4 pr-4 py-3 my-6 rounded-r bg-muted/40",
  {
    variants: {
      type: {
        note: "border-l-foreground/60",
        warning: "border-l-foreground",
        tip: "border-l-foreground/40",
      },
    },
    defaultVariants: { type: "note" },
  }
);

export function Callout({
  type = "note",
  title,
  children,
}: {
  type?: CalloutType;
  title?: string;
  children: ReactNode;
}) {
  return (
    <div data-callout={type} className={cn(calloutVariants({ type }))}>
      {title && <div className="text-sm font-semibold mb-1">{title}</div>}
      <div className="text-sm">{children}</div>
    </div>
  );
}
