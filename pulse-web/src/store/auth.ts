/**
 * Auth store: 持久化登录态（token + user）。
 *
 * persist 中间件把 token/user/isAuthenticated 写入 localStorage（key: stockpulse-auth），
 * 刷新页面后由 ProtectedRoute 调用 getMe() 校验 token 是否仍有效。
 *
 * 安全提示：JWT 存 localStorage 在 XSS 下会被读走；个人项目场景下接受该风险，
 * 后续如多用户化需迁移到 httpOnly cookie + CSRF token。
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type User = {
  id: string;
  username: string;
  createdAt: string;
};

type AuthState = {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      login: (token, user) => set({ token, user, isAuthenticated: true }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name: "stockpulse-auth",
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
