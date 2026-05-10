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

  // 解析 JSON 失败兜底为空对象，避免 502/网关错误页面响应导致 data.error 报错
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
