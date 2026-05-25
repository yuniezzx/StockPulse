import type { ComponentType } from "react";
import { Prose, mdxComponents } from "@/components/indicator-doc/prose";

const modules = import.meta.glob<{ default: ComponentType<{ components: typeof mdxComponents }> }>(
  "../../content/indicator-doc/momentum/*.mdx",
  { eager: true }
);

export default function IndicatorMomentumPage() {
  const components = Object.entries(modules)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, mod]) => mod.default);

  if (components.length === 0) {
    return (
      <Prose>
        <p className="text-muted-foreground text-sm">内容待补充。</p>
      </Prose>
    );
  }

  return (
    <Prose>
      {components.map((Component, i) => (
        <Component key={i} components={mdxComponents} />
      ))}
    </Prose>
  );
}