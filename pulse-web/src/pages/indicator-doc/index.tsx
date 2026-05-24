import { Link } from "react-router-dom";
import { indicatorDocNav } from "@/lib/indicator-doc-nav";

export default function IndicatorDocPage() {
  return (
    <div className="p-8">
      <h1 className="mb-2 text-2xl font-semibold">指标文档</h1>
      <p className="text-muted-foreground mb-6 text-sm">
        客观技术指标与布尔特征的定义、公式与边界情况说明。
      </p>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {indicatorDocNav.map((section) => (
          <Link
            key={section.slug}
            to={`/indicator-doc/${section.slug}`}
            className="hover:bg-accent rounded-lg border p-4 transition-colors"
          >
            <div className="mb-2 font-semibold">{section.title}</div>
            <ul className="text-muted-foreground space-y-0.5 text-sm">
              {section.items.map((item) => (
                <li key={item.anchor}>· {item.title}</li>
              ))}
            </ul>
          </Link>
        ))}
      </div>
    </div>
  );
}
