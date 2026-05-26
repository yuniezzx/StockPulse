import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type TocEntry = {
  id: string;
  text: string;
};

export function DocToc({ containerSelector = "[data-doc-content]" }: { containerSelector?: string }) {
  const [entries, setEntries] = useState<TocEntry[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Scan h2[id] elements from the content container
  useEffect(() => {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const headings = Array.from(container.querySelectorAll("h2[id]")) as HTMLElement[];
    setEntries(
      headings.map((h) => ({
        id: h.id,
        text: h.textContent?.trim() ?? "",
      }))
    );

    // Set up IntersectionObserver for scroll-spy
    observerRef.current?.disconnect();
    observerRef.current = new IntersectionObserver(
      (entries) => {
        // Find the topmost intersecting heading
        const intersecting = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (intersecting.length > 0) {
          setActiveId(intersecting[0].target.id);
        }
      },
      {
        rootMargin: "-20% 0px -70% 0px",
      }
    );

    headings.forEach((h) => observerRef.current?.observe(h));

    return () => observerRef.current?.disconnect();
  }, [containerSelector]);

  if (entries.length === 0) return null;

  return (
    <aside
      className="hidden xl:block w-56 shrink-0 sticky top-14 max-h-[calc(100vh-3.5rem)] overflow-y-auto self-start py-12 pr-6"
      data-toc
    >
      <div className="mb-3 pl-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        本页目录
      </div>
      <ul className="space-y-1.5">
        {entries.map((entry) => (
          <li key={entry.id}>
            <a
              href={`#${entry.id}`}
              data-toc-item={entry.id}
              data-active={activeId === entry.id ? "true" : "false"}
              className={cn(
                "block border-l-2 py-1 pl-3 text-xs transition-colors",
                activeId === entry.id
                  ? "border-l-foreground text-foreground"
                  : "border-l-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {entry.text}
            </a>
          </li>
        ))}
      </ul>
    </aside>
  );
}