"use client";

/**
 * Cliente HTTP unico da aplicacao.
 *
 * Seguranca: nenhum token e guardado em JS. A sessao vive em cookies HttpOnly e
 * o unico valor lido pelo browser e o cookie csrf_token (double submit), enviado
 * de volta no header X-CSRF-Token nas rotas mutaveis.
 */

const BASE_URL = "/api";
const CSRF_COOKIE = "csrf_token";
const CSRF_HEADER = "X-CSRF-Token";
const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const found = document.cookie
    .split("; ")
    .find((part) => part.startsWith(`${CSRF_COOKIE}=`));
  return found ? decodeURIComponent(found.slice(CSRF_COOKIE.length + 1)) : null;
}

async function ensureCsrf(): Promise<string | null> {
  const existing = readCsrfCookie();
  if (existing) return existing;
  await fetch(`${BASE_URL}/auth/csrf`, { credentials: "include", cache: "no-store" });
  return readCsrfCookie();
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (MUTATING.has(method)) {
    const token = await ensureCsrf();
    if (token) headers.set(CSRF_HEADER, token);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
    cache: "no-store",
  });

  const raw = await response.text();
  const body = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};

  if (!response.ok) {
    throw new ApiError(
      response.status,
      String(body.error ?? "error"),
      String(body.message ?? "Nao foi possivel completar a operacao."),
    );
  }
  return body as T;
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T,>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
};
