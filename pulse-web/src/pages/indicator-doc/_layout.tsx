import { Outlet } from "react-router-dom";
import { DocNav } from "@/components/indicator-doc/doc-nav";

export default function IndicatorDocLayout() {
  return (
    <div className="flex min-h-0 flex-1">
      <DocNav />
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
