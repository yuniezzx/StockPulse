/**
 * HTTP client: pulse-web 与 pulse-api 之间的唯一出口。
 *
 * 所有 lib/api/*.ts 的请求函数都走 apiFetch，统一负责：
 *   - 注入 JWT（从 zustand auth store 读取）
 *   - 反序列化失败兜底（502/网关 HTML 响应不会让 data.error 抛 TypeError）
 *   - 把非 2xx 翻译成 ApiError（statusCode + error name + message + zod issues）
 *
 * 调用方按 `instanceof ApiError` 判错（见 pages/login.tsx 的用法）。
 */
import { useAuthStore } from "@/store/auth";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!BASE_URL) {
  throw new Error("VITE_API_BASE_URL is not set. Check web/.env");
}

export class ApiError extends Error {
  status: number;
  error: string;
  issues?: unknown;

  constructor(status: number, error: string, message: string, issues?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.error = error;
    this.issues = issues;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token;

  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  const data = (await res.json().catch(() => ({}))) as {
    error?: string;
    message?: string;
    issues?: unknown;
  };

  if (!res.ok) {
    throw new ApiError(
      res.status,
      data.error ?? "UnknownError",
      data.message ?? res.statusText,
      data.issues,
    );
  }

  return data as T;
}
