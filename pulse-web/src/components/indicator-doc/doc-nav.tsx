import { useLocation, Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { indicatorDocNav } from "@/lib/indicator-doc-nav";

export function DocNav() {
  const { pathname } = useLocation();

  return (
    <nav
      className="bg-background w-60 shrink-0 sticky top-14 max-h-[calc(100vh-3.5rem)] overflow-y-auto self-start border-r py-6"
      data-doc-nav
    >
      <div className="space-y-1.5 px-3">
        {indicatorDocNav.map((section) => {
          const sectionPath = `/indicator-doc/${section.slug}`;
          const isActive = pathname === sectionPath;

          return (
            <Link
              key={section.slug}
              to={sectionPath}
              data-doc-nav-section
              className={cn(
                "block rounded-sm border-l-2 py-1.5 pl-3 pr-2 text-sm transition-colors",
                isActive
                  ? "border-l-foreground bg-muted/40 text-foreground font-semibold"
                  : "border-l-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {section.title}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}