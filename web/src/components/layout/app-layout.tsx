import { Outlet } from "react-router-dom";
export default function AppLayout() {
  return (
    <div className="min-h-screen">
      {/* 侧边栏占位 */}
      <main>
        <Outlet />
      </main>
    </div>
  );
}
