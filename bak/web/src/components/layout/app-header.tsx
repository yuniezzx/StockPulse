import { useLocation } from "react-router-dom";
import { Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { mainNavItems, footerNavItems } from "@/lib/nav";

function getPageTitle(pathname: string): string {
  const all = [...mainNavItems, ...footerNavItems];
  const exact = all.find((i) => i.url === pathname);
  if (exact) return exact.title;
  const prefix = all.find((i) => i.url !== "/" && pathname.startsWith(i.url));
  if (prefix) return prefix.title;
  if (pathname === "/login") return "登录";
  return "未知页面";
}

export function AppHeader() {
  const { pathname } = useLocation();
  const title = getPageTitle(pathname);

  return (
    <header className="bg-background sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b px-4">
      <SidebarTrigger />
      <Separator orientation="vertical" className="mx-1 h-4" />
      <span className="text-sm font-medium">{title}</span>

      <div className="ml-auto flex items-center gap-2">
        <Button variant="ghost" size="icon" aria-label="切换主题">
          <Moon />
        </Button>
      </div>
    </header>
  );
}
