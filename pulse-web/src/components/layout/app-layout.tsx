import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppHeader } from "@/components/layout/app-header";

const COLLAPSED_PATH_PREFIXES = ["/indicator-doc"];

export default function AppLayout() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(true);

  useEffect(() => {
    const shouldCollapse = COLLAPSED_PATH_PREFIXES.some((p) => pathname.startsWith(p));
    setOpen(!shouldCollapse);
  }, [pathname]);

  return (
    <SidebarProvider open={open} onOpenChange={setOpen}>
      <AppSidebar />
      <SidebarInset>
        <AppHeader />
        <main className="flex flex-1 flex-col">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
