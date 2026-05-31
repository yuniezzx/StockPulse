import { Link } from "react-router-dom";
import { indicatorDocNav, type DocNavItem } from "@/lib/indicator-doc-nav";

export default function IndicatorDocPage() {
  return (
    <div className="mx-auto max-w-3xl px-8 py-12">
      <h1 className="mb-2 text-3xl font-semibold tracking-tight">指标文档</h1>
      <p className="mb-10 text-[15px] text-muted-foreground">
        客观技术指标与布尔特征的定义、公式与边界情况说明。
      </p>

      <div className="mt-10 grid grid-cols-2 gap-4">
        {indicatorDocNav.map((section) => (
          <div
            key={section.slug}
            className="rounded-md border border-border p-6"
          >
            <div className="mb-4 text-xs uppercase tracking-wide text-muted-foreground">
              {section.title}
            </div>
            <ul className="space-y-3">
              {section.items.map((item) => (
                <li key={item.anchor} className="text-sm">
                  <Link
                    to={`/indicator-doc/${section.slug}#${item.anchor}`}
                    className="text-muted-foreground hover:text-foreground hover:underline underline-offset-4 transition-colors"
                  >
                    {item.title}
                  </Link>
                  {(item as DocNavItem).hint && (
                    <span className="ml-2 text-xs text-muted-foreground/60">
                      {(item as DocNavItem).hint}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
