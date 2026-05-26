import { Outlet } from "react-router-dom";
import { DocNav } from "@/components/indicator-doc/doc-nav";
import { DocToc } from "@/components/indicator-doc/doc-toc";

export default function IndicatorDocLayout() {
  return (
    <div className="flex flex-1 min-h-0">
      <DocNav />
      <main
        className="flex-1 overflow-y-auto"
        data-doc-content
      >
        <Outlet />
      </main>
      <DocToc />
    </div>
  );
}
