import {
  Home,
  LayoutDashboard,
  Target,
  Search,
  Briefcase,
  TrendingUp,
  AlertTriangle,
  Sliders,
  LineChart,
  Settings,
  BookOpen,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  title: string;
  url: string;
  icon: LucideIcon;
};

export const mainNavItems: NavItem[] = [
  { title: "主页", url: "/", icon: Home },
  { title: "仪表盘", url: "/dashboard", icon: LayoutDashboard },
  { title: "选股", url: "/picks", icon: Target },
  { title: "个股分析", url: "/analysis", icon: Search },
  { title: "持仓", url: "/portfolio", icon: Briefcase },
  { title: "虚拟仓", url: "/virtual-portfolio", icon: TrendingUp },
  { title: "风控信号", url: "/risk-signals", icon: AlertTriangle },
  { title: "策略与权重", url: "/strategies", icon: Sliders },
  { title: "校验报告", url: "/evaluations", icon: LineChart },
];

export const footerNavItems: NavItem[] = [
  { title: "设置", url: "/settings", icon: Settings },
];

export const topbarNavItems: NavItem[] = [
  { title: "指标文档", url: "/indicator-doc", icon: BookOpen },
];
