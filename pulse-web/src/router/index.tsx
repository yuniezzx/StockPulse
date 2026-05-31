/**
 * Router: 路由树 + 鉴权门控。
 *
 * 两层守卫：
 *   GuestRoute      已登录则 redirect 到 /，用于 /login & /register
 *   ProtectedRoute  未登录则 redirect 到 /login，校验 token 后渲染 AppLayout
 *
 * 通配 "*" 兜底到 "/"，避免脏 URL 直接显示空白。
 */
import { createBrowserRouter, Navigate } from "react-router-dom";
import LoginPage from "@/pages/login";
import RegisterPage from "@/pages/register";
import HomePage from "@/pages/home";
import DashboardPage from "@/pages/dashboard";
import PicksPage from "@/pages/picks/index";
import AnalysisPage from "@/pages/analysis/index";
import PortfolioPage from "@/pages/portfolio/index";
import VirtualPortfolioPage from "@/pages/virtual-portfolio/index";
import RiskSignalsPage from "@/pages/risk-signals/index";
import StrategiesPage from "@/pages/strategies/index";
import EvaluationsPage from "@/pages/evaluations/index";
import SettingsPage from "@/pages/settings/index";
import IndicatorDocLayout from "@/pages/indicator-doc/_layout";
import IndicatorDocPage from "@/pages/indicator-doc/index";
import IndicatorToolsPage from "@/pages/indicator-doc/tools";
import IndicatorTrendPage from "@/pages/indicator-doc/trend";
import IndicatorMomentumPage from "@/pages/indicator-doc/momentum";
import IndicatorVolumePage from "@/pages/indicator-doc/volume";
import IndicatorMoneyflowPage from "@/pages/indicator-doc/moneyflow";
import AppLayout from "@/components/layout/app-layout";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { GuestRoute } from "@/components/auth/guest-route";

export const router = createBrowserRouter([
  {
    element: <GuestRoute />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: "/",
        element: <AppLayout />,
        children: [
          { index: true, element: <HomePage /> },
          { path: "dashboard", element: <DashboardPage /> },
          { path: "picks", element: <PicksPage /> },
          { path: "analysis", element: <AnalysisPage /> },
          { path: "portfolio", element: <PortfolioPage /> },
          { path: "virtual-portfolio", element: <VirtualPortfolioPage /> },
          { path: "risk-signals", element: <RiskSignalsPage /> },
          { path: "strategies", element: <StrategiesPage /> },
          { path: "evaluations", element: <EvaluationsPage /> },
          { path: "settings", element: <SettingsPage /> },
          {
            path: "indicator-doc",
            element: <IndicatorDocLayout />,
            children: [
              { index: true, element: <IndicatorDocPage /> },
              { path: "tools", element: <IndicatorToolsPage /> },
              { path: "trend", element: <IndicatorTrendPage /> },
              { path: "momentum", element: <IndicatorMomentumPage /> },
              { path: "volume", element: <IndicatorVolumePage /> },
              { path: "moneyflow", element: <IndicatorMoneyflowPage /> },
            ],
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
