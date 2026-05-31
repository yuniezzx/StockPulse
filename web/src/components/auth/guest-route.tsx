import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/auth";

export function GuestRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
