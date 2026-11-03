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
export type SurveyResponse = components["schemas"]["SurveyResponse"];
export type SurveyList = components["schemas"]["SurveyList"];
export type TechnicianOption = components["schemas"]["TechnicianOption"];
export type QuotationResponse = components["schemas"]["QuotationResponse"];
export type QuotationList = components["schemas"]["QuotationList"];
export type QuotationLineResponse = components["schemas"]["QuotationLineResponse"];
export type RevisionRequestResponse = components["schemas"]["RevisionRequestResponse"];
export type PaymentRequirementResponse = components["schemas"]["PaymentRequirementResponse"];
export type PaymentIntentResponse = components["schemas"]["PaymentIntentResponse"];
export type OrderResponse = components["schemas"]["OrderResponse"];
export type OrderList = components["schemas"]["OrderList"];
export type WarehouseRequestResponse = components["schemas"]["WarehouseRequestResponse"];
export type SchedulingRequestResponse = components["schemas"]["SchedulingRequestResponse"];
export type TemplateVersionResponse = components["schemas"]["TemplateVersionResponse"];
export type PackageResponseList = PackageResponse[];

export function idempotencyKey(): string {
  return crypto.randomUUID();
}

export const sandboxPaymentsEnabled = process.env.NEXT_PUBLIC_SOLAROPS_ENV === "development";

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
  const isForm = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (init.body && !isForm && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
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
