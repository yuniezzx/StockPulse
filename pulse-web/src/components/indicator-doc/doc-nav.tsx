import { useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { indicatorDocNav } from "@/lib/indicator-doc-nav";

export function DocNav() {
  const { pathname, hash } = useLocation();

  return (
    <nav
      className="bg-background w-60 shrink-0 overflow-y-auto border-r py-6"
      data-doc-nav
    >
      {indicatorDocNav.map((section) => {
        const sectionPath = `/indicator-doc/${section.slug}`;

        return (
          <div key={section.slug} className="mb-8 px-3" data-doc-nav-section>
            {/* Section header — not a link, just a label */}
            <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {section.title}
            </div>

            {/* All items always visible */}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const itemHref = `${sectionPath}#${item.anchor}`;
                const isActive =
                  pathname === sectionPath && hash === `#${item.anchor}`;

                return (
                  <li key={item.anchor}>
                    <a
                      href={itemHref}
                      data-doc-nav-item={item.anchor}
                      className={cn(
                        "block rounded-sm border-l-2 py-1 pl-3 pr-2 text-sm transition-colors",
                        isActive
                          ? "border-l-foreground bg-muted/40 text-foreground"
                          : "border-l-transparent text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {item.title}
                      {'hint' in item && item.hint && (
                        <span className="ml-1.5 text-xs text-muted-foreground/60">
                          {item.hint}
                        </span>
                      )}
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
