import type { ReactNode } from "react";
import { indicatorDocNav, type DocNavSection } from "@/lib/indicator-doc-nav";

type Props = {
  slug: DocNavSection["slug"];
  /** 锚点 -> 该锚点的富内容；未提供的锚点显示"待补充"占位。 */
  content?: Record<string, ReactNode>;
};

export function IndicatorSectionPage({ slug, content }: Props) {
  const section = indicatorDocNav.find((s) => s.slug === slug);
  if (!section) return null;

  return (
    <article className="max-w-3xl p-8">
      <h1 className="mb-6 text-2xl font-semibold">{section.title}</h1>
      <div className="space-y-10">
        {section.items.map((item) => {
          const body = content?.[item.anchor];
          return (
            <section key={item.anchor} id={item.anchor} className="scroll-mt-20">
              <h2 className="mb-2 text-lg font-semibold">
                {item.title}
                {item.hint && (
                  <span className="text-muted-foreground ml-2 text-sm font-normal">
                    {item.hint}
                  </span>
                )}
              </h2>
              {body ?? (
                <p className="text-muted-foreground text-sm">
                  待补充：公式 / 边界 / 示例。
                </p>
              )}
            </section>
          );
        })}
      </div>
    </article>
  );
}
