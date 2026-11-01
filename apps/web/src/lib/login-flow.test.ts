import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { signInWithPassword, verifyLoginFactor } from "./login-flow";
const fetchMock = vi.fn();
const payload = { identifier: "fixture@example.com", password: "fixture-password", account_kind: "customer" as const };
beforeEach(() => { vi.stubGlobal("fetch", fetchMock); vi.stubGlobal("document", { cookie: "solarops_csrf=fixture-csrf" }); });
afterEach(() => { vi.unstubAllGlobals(); vi.resetAllMocks(); });
function reply(body: unknown, status = 200) { fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(body), { status })); }
it("retains password login for accounts without MFA and sends credentials through the CSRF transport", async () => {
  reply({ user: { id: "fixture", role: "customer" } });
  expect(await signInWithPassword(payload)).toMatchObject({ kind: "authenticated", user: { id: "fixture" } });
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(payload);
  expect(fetchMock.mock.calls[0][1].headers.get("X-CSRF-Token")).toBe("fixture-csrf");
});
it("holds the login at a second-factor challenge even if a response also contains user context", async () => {
  reply({ mfa_required: true, ticket: "opaque-ticket", user: { role: "admin" } });
  expect(await signInWithPassword(payload)).toEqual({ kind: "second_factor", ticket: "opaque-ticket" });
});
it("fails closed when an MFA challenge has no ticket", async () => {
  reply({ mfa_required: true });
  await expect(signInWithPassword(payload)).rejects.toThrow("challenge was unavailable");
});
it("uses the TOTP ticket endpoint and only accepts an authenticated supported account", async () => {
  reply({ user: { role: "technician" } });
  expect(await verifyLoginFactor("ticket", " 012345 ")).toMatchObject({ role: "technician" });
  expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/auth/mfa/ticket/verify-totp");
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ ticket: "ticket", code: "012345" });
});
it("sends recovery codes to recovery verification without falling back on failure", async () => {
  reply({ error: { code: "invalid_recovery", message: "Recovery code rejected" } }, 401);
  await expect(verifyLoginFactor("ticket", "ABCD-2345")).rejects.toThrow("Recovery code rejected");
  expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/auth/mfa/ticket/verify-recovery");
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
it("does not accept a successful response without a valid account", async () => {
  reply({});
  await expect(verifyLoginFactor("ticket", "012345")).rejects.toThrow("authenticated account");
});
