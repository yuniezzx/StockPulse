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
