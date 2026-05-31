/**
 * Auth API: 注册 / 登录 / getMe。
 *
 * 字段命名严格 camelCase，与 pulse-api/src/domains/auth/schemas.ts 对齐
 * （AGENTS.md §1 跨语言契约）。snake_case 转换由 pulse-api repository 层处理。
 */
import { apiFetch } from "./client";

export interface PublicUser {
  id: string;
  username: string;
  createdAt: string;
}

export interface AuthSuccess {
  token: string;
  user: PublicUser;
}

export interface MeResponse {
  user: PublicUser;
}

export interface AuthInput {
  username: string;
  password: string;
}

export function register(input: AuthInput): Promise<AuthSuccess> {
  return apiFetch<AuthSuccess>("/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function login(input: AuthInput): Promise<AuthSuccess> {
  return apiFetch<AuthSuccess>("/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getMe(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/auth/me");
}
