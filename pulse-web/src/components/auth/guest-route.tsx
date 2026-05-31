/**
 * GuestRoute: 已登录用户访问 /login & /register 时强制 redirect 到 /。
 *
 * 与 ProtectedRoute 不同：只读 isAuthenticated 同步状态，不发请求校验
 * （登录页 token 校验交给跳转后的 ProtectedRoute 做，避免双重网络请求）。
 */
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/auth";

export function GuestRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
