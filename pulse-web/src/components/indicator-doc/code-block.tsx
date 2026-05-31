import type { ReactNode } from "react";

export function CodeBlock({ children, ...props }: { children: ReactNode; [key: string]: unknown }) {
  return (
    <figure
      className="my-6 overflow-hidden rounded-md border text-[13px] leading-6"
      {...props}
    >
      {children}
    </figure>
  );
}
