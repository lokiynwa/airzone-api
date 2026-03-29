import { apiFetch } from "../../lib/api";

export type AuthUser = {
  id: number;
  email: string;
};

export type AuthResponse = {
  user: AuthUser;
};

export type AuthPayload = {
  email: string;
  password: string;
};

export async function fetchCurrentUser() {
  return apiFetch<AuthResponse>("/auth/me");
}

export async function login(payload: AuthPayload) {
  return apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function register(payload: AuthPayload) {
  return apiFetch<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logout() {
  await apiFetch<void>("/auth/logout", {
    method: "POST",
  });
}

