import type { components } from "@/generated/schema";
import { api, type CurrentUser } from "@/lib/api";
import { isRole } from "@/lib/access";

export type LoginOutcome = { kind: "second_factor"; ticket: string } | { kind: "authenticated"; user: CurrentUser };
type LoginReply = { user?: CurrentUser; mfa_required?: boolean; ticket?: string };

function requireUser(reply: LoginReply): CurrentUser {
  if (!reply.user || !isRole(reply.user.role)) throw new Error("Sign-in did not return a supported authenticated account.");
  return reply.user;
}

export async function signInWithPassword(payload: components["schemas"]["LoginRequest"]): Promise<LoginOutcome> {
  const reply = await api<LoginReply>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(payload) });
  if (reply.mfa_required) {
    if (!reply.ticket) throw new Error("The second-factor challenge was unavailable. Sign in again.");
    return { kind: "second_factor", ticket: reply.ticket };
  }
  return { kind: "authenticated", user: requireUser(reply) };
}

export async function verifyLoginFactor(ticket: string, enteredCode: string): Promise<CurrentUser> {
  const code = enteredCode.trim();
  const endpoint = /^[A-Za-z2-9]{4}-[A-Za-z2-9]{4}$/.test(code)
    ? "/api/v1/auth/mfa/ticket/verify-recovery"
    : "/api/v1/auth/mfa/ticket/verify-totp";
  const reply = await api<LoginReply>(endpoint, { method: "POST", body: JSON.stringify({ ticket, code }) });
  return requireUser(reply);
}
