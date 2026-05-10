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
