import type { components } from "@/generated/schema";

export type CurrentUser = components["schemas"]["CurrentUser"];
export type EnquiryDetail = components["schemas"]["EnquiryDetail"];
export type EnquirySummary = components["schemas"]["EnquirySummary"];
export type EnquiryList = components["schemas"]["EnquiryList"];
export type EnquiryCreate = components["schemas"]["EnquiryCreate"];
export type PackageResponse = components["schemas"]["PackageResponse"];
export type EmployeeResponse = components["schemas"]["EmployeeResponse"];
export type EmployeeCreate = components["schemas"]["EmployeeCreate"];
export type QualificationUpdate = components["schemas"]["QualificationUpdate"];

export class ApiError extends Error {
  status: number;
  code: string;
  details: { field?: string | null; message: string }[];

  constructor(status: number, code: string, message: string, details: ApiError["details"] = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function csrfFromCookie(): string | null {
  const row = document.cookie.split("; ").find((part) => part.startsWith("solarops_csrf="));
  return row ? decodeURIComponent(row.slice("solarops_csrf=".length)) : null;
}

async function ensureCsrf(): Promise<string> {
  const existing = csrfFromCookie();
  if (existing) return existing;
  const response = await fetch("/api/v1/auth/csrf", { credentials: "include" });
  const body = (await response.json()) as components["schemas"]["CsrfResponse"];
  if (!response.ok || !body.csrf_token) {
    throw new ApiError(response.status, "csrf_failed", "Could not start a secure form token.");
  }
  return body.csrf_token;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const method = (init.method ?? "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    headers.set("X-CSRF-Token", await ensureCsrf());
  }
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json()) as T & {
    error?: { code: string; message: string; details?: ApiError["details"] };
  };
  if (!response.ok) {
    const error = payload.error;
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? "The request failed.",
      error?.details ?? [],
    );
  }
  return payload;
}

export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {};
  const map: Record<string, string> = {};
  for (const detail of error.details) {
    if (detail.field) map[detail.field] = detail.message;
  }
  return map;
}
