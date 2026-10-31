// Scenario B — MFA and recovery in a real browser.
//
// Employee enrolls a TOTP second factor -> password login stops at a ticket ->
// TOTP code completes sign-in -> wrong codes are rejected -> recovery code
// signs in without privilege escalation -> revoked factor restores direct login.
import { createHmac } from "crypto";
import { expect, test } from "@playwright/test";

const TECH = { identifier: "EMP-TECH-4E", password: "PreviewTech123" };

function totpNow(secretBase32: string, atMs = Date.now()): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const char of secretBase32.replace(/=+$/, "").toUpperCase()) {
    bits += alphabet.indexOf(char).toString(2).padStart(5, "0");
  }
  const key = Buffer.from(bits.match(/.{1,8}/g)!.map((byte) => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(atMs / 30000)));
  const digest = createHmac("sha1", key).update(counter).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const code =
    ((digest[offset] & 0x7f) << 24) |
    (digest[offset + 1] << 16) |
    (digest[offset + 2] << 8) |
    digest[offset + 3];
  return (code % 1_000_000).toString().padStart(6, "0");
}

async function gotoLogin(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.waitForFunction(() => document.body.dataset.loginReady === "1");
}

async function apiLogout(page: import("@playwright/test").Page) {
  const csrf = await page.request.get("/api/v1/auth/csrf");
  const token = (await csrf.json()).csrf_token as string;
  const loggedOut = await page.request.post("/api/v1/auth/logout", {
    headers: { "X-CSRF-Token": token },
  });
  if (![204, 401].includes(loggedOut.status())) {
    throw new Error(`logout failed with ${loggedOut.status()}`);
  }
}

test("TOTP enrollment, ticket login, recovery, revocation", async ({ page }) => {
  await gotoLogin(page);
  await page.getByLabel("I am signing in as").selectOption("technician");
  await page.getByLabel("Employee ID").fill(TECH.identifier);
  await page.locator('input[name="password"]').fill(TECH.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/technician/);

  await page.goto("/security");
  // Rerun-safe: clear any factor left by a previous run.
  await page
    .getByRole("button", { name: /Enroll authenticator app|Revoke authenticator app/ })
    .first()
    .waitFor();
  if (await page.getByRole("button", { name: "Revoke authenticator app" }).count()) {
    page.once("dialog", (dialog) => dialog.accept(TECH.password));
    await page.getByRole("button", { name: "Revoke authenticator app" }).click();
    await expect(page.getByText("revoked")).toBeVisible();
  }
  page.once("dialog", (dialog) => dialog.accept(TECH.password));
  await page.getByRole("button", { name: "Enroll authenticator app" }).click();
  await expect(page.getByText("Manual key:")).toBeVisible();
  const keyText = (await page.getByText("Manual key:").textContent()) ?? "";
  const secret = keyText.replace("Manual key:", "").trim();
  expect(secret.length).toBeGreaterThan(10);
  await page.getByLabel("6-digit code").fill(totpNow(secret));
  await page.getByRole("button", { name: "Confirm enrollment" }).click();
  await expect(page.getByText("Authenticator app is enrolled")).toBeVisible();

  // Wrong codes are rejected on the second-factor step.
  await apiLogout(page);
  await gotoLogin(page);
  await page.getByLabel("I am signing in as").selectOption("technician");
  await page.getByLabel("Employee ID").fill(TECH.identifier);
  await page.locator('input[name="password"]').fill(TECH.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText("Your password was correct")).toBeVisible();
  await page.getByLabel("Second-factor code").fill("000000");
  await page.getByRole("button", { name: "Verify and sign in" }).click();
  await expect(page.getByText("incorrect")).toBeVisible();

  await page.getByLabel("Second-factor code").fill(totpNow(secret));
  await page.getByRole("button", { name: "Verify and sign in" }).click();
  await expect(page).toHaveURL(/\/technician/);
  const me = await page.request.get("/api/v1/auth/me");
  expect((await me.json()).user.role).toBe("technician");

  // Recovery codes: issue, then use one without gaining privileges.
  await page.goto("/security");
  page.once("dialog", (dialog) => dialog.accept(TECH.password));
  await page.getByRole("button", { name: /recovery codes/ }).click();
  const codes = page.getByRole("list", { name: "Recovery codes" });
  await expect(codes).toBeVisible();
  const firstCode = ((await codes.getByRole("listitem").first().textContent()) ?? "").trim();
  expect(firstCode).toMatch(/^[A-Z2-9]{4}-[A-Z2-9]{4}$/);

  await apiLogout(page);
  await gotoLogin(page);
  await page.getByLabel("I am signing in as").selectOption("technician");
  await page.getByLabel("Employee ID").fill(TECH.identifier);
  await page.locator('input[name="password"]').fill(TECH.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByLabel("Second-factor code").fill(firstCode);
  await page.getByRole("button", { name: "Verify and sign in" }).click();
  await expect(page).toHaveURL(/\/technician/);
  const recovered = await (await page.request.get("/api/v1/auth/me")).json();
  expect(recovered.user.role).toBe("technician");

  // Revoking the factor restores direct password login.
  await page.goto("/security");
  page.once("dialog", (dialog) => dialog.accept(TECH.password));
  await page.getByRole("button", { name: "Revoke authenticator app" }).click();
  await expect(page.getByText("revoked")).toBeVisible();

  await apiLogout(page);
  await gotoLogin(page);
  await page.getByLabel("I am signing in as").selectOption("technician");
  await page.getByLabel("Employee ID").fill(TECH.identifier);
  await page.locator('input[name="password"]').fill(TECH.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/technician/);
});
