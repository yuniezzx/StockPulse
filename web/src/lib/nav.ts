import {
  Home,
  LayoutDashboard,
  Briefcase,
  TrendingUp,
  ArrowLeftRight,
  LineChart,
  FlaskConical,
  Settings,
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
  { title: "投资组合", url: "/portfolio", icon: Briefcase },
  { title: "持仓", url: "/holdings", icon: TrendingUp },
  { title: "交易", url: "/transactions", icon: ArrowLeftRight },
  { title: "行情", url: "/market", icon: LineChart },
  { title: "回测", url: "/backtest", icon: FlaskConical },
];

export const footerNavItems: NavItem[] = [
  { title: "设置", url: "/settings", icon: Settings },
];
