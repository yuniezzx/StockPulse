import { createBrowserRouter, Navigate } from "react-router-dom";
import LoginPage from "@/pages/login";
import HomePage from "@/pages/home";
import DashboardPage from "@/pages/dashboard";
import PlaceholderPage from "@/pages/placeholder";
import AppLayout from "@/components/layout/app-layout";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { GuestRoute } from "@/components/auth/guest-route";

export const router = createBrowserRouter([
  {
    element: <GuestRoute />,
    children: [{ path: "/login", element: <LoginPage /> }],
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
          { path: "portfolio", element: <PlaceholderPage /> },
          { path: "holdings", element: <PlaceholderPage /> },
          { path: "transactions", element: <PlaceholderPage /> },
          { path: "market", element: <PlaceholderPage /> },
          { path: "backtest", element: <PlaceholderPage /> },
          { path: "settings", element: <PlaceholderPage /> },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
