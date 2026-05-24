import { NavLink, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { indicatorDocNav } from "@/lib/indicator-doc-nav";

export function DocNav() {
  const { pathname, hash } = useLocation();

  return (
    <nav className="bg-background w-60 shrink-0 overflow-y-auto border-r py-4">
      {indicatorDocNav.map((section) => {
        const sectionPath = `/indicator-doc/${section.slug}`;
        const sectionActive = pathname === sectionPath;

        return (
          <div key={section.slug} className="mb-4 px-3">
            <NavLink
              to={sectionPath}
              className={({ isActive }) =>
                cn(
                  "block py-1.5 text-sm font-semibold transition-colors",
                  isActive
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )
              }
            >
              {section.title}
            </NavLink>

            {sectionActive && (
              <ul className="mt-1 ml-2 border-l">
                {section.items.map((item) => {
                  const itemActive = hash === `#${item.anchor}`;
                  return (
                    <li key={item.anchor}>
                      <a
                        href={`${sectionPath}#${item.anchor}`}
                        className={cn(
                          "-ml-px block border-l py-1 pl-3 text-xs transition-colors",
                          itemActive
                            ? "border-foreground text-foreground"
                            : "text-muted-foreground hover:text-foreground border-transparent",
                        )}
                      >
                        {item.title}
                        {item.hint && (
                          <span className="text-muted-foreground/60 ml-1">{item.hint}</span>
                        )}
                      </a>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        );
      })}
    </nav>
  );
}
