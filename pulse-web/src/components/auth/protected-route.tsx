/**
 * ProtectedRoute: 校验 token 后才渲染子路由。
 *
 * 三态状态机（避免 token 失效时闪现内部页面）：
 *   checking         调用 getMe()，渲染 loading 占位
 *   ok               getMe 成功 -> Outlet 渲染受保护页面
 *   unauthenticated  401 或无 token -> Navigate 到 /login
 *   network-error    其他错误 -> 错误提示而非跳转（避免登录态被网络问题误清）
 *
 * cancelled 标志位防 unmount 后 setState（StrictMode 双调用安全）。
 */
import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { getMe } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

type Status = "checking" | "ok" | "unauthenticated" | "network-error";

export const ProtectedRoute = () => {
  const token = useAuthStore((s) => s.token);
  const setAuth = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);

  const [status, setStatus] = useState<Status>(token ? "checking" : "unauthenticated");

  useEffect(() => {
    if (!token) return;

    let cancelled = false;
    (async () => {
      try {
        const { user } = await getMe();
        if (cancelled) return;
        setAuth(token, user);
        setStatus("ok");
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          logout();
          setStatus("unauthenticated");
        } else {
          setStatus("network-error");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [token, setAuth, logout]);

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace />;
  }

  if (status === "network-error") {
    return (
      <div className="bg-background flex min-h-screen items-center justify-center p-4">
        <div className="max-w-sm rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          无法连接到 API 服务。请检查后端是否运行，然后刷新页面。
        </div>
      </div>
    );
  }

  if (status === "checking") {
    return (
      <div className="bg-background flex min-h-screen items-center justify-center p-4">
        <div className="text-muted-foreground text-sm">验证登录状态...</div>
      </div>
    );
  }

  return <Outlet />;
};
