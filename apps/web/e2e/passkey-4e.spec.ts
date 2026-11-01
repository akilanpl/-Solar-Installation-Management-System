// Scenario A — Passkey authentication end to end with a virtual authenticator.
//
// Customer signs up -> logs in with password -> registers a passkey ->
// logs out -> logs in with the passkey -> sees only their own records ->
// revokes the passkey -> the revoked credential no longer works.
import { expect, test, type Page } from "@playwright/test";

const CUSTOMER = {
  name: "Asha Acceptance",
  email: `accept-passkey-${Date.now()}@example.com`,
  phone: "9845012345",
  password: "Acceptance123",
};

async function addVirtualAuthenticator(page: Page): Promise<string> {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("WebAuthn.enable");
  const { authenticatorId } = await cdp.send("WebAuthn.addVirtualAuthenticator", {
    options: {
      protocol: "ctap2",
      transport: "internal",
      hasResidentKey: true,
      hasUserVerification: true,
      isUserVerified: true,
      automaticPresenceSimulation: true,
    },
  });
  return authenticatorId as string;
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

test("passkey registration, login, revocation", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));
  process.on("exit", () => {
    if (consoleErrors.length > 0) console.log(`PAGE ERRORS:\n${consoleErrors.join("\n")}`);
  });
  await page.goto("/signup");
  await page.waitForFunction(() => document.body.dataset.signupReady === "1");
  await page.getByLabel("Full name").fill(CUSTOMER.name);
  await page.getByLabel("Email").fill(CUSTOMER.email);
  await page.getByLabel("Mobile").fill(CUSTOMER.phone);
  await page.locator('input[name="password"]').fill(CUSTOMER.password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/verify-email/);

  await page.waitForFunction(() => document.body.dataset.verifyReady === "1");
  await page.getByRole("button", { name: /mailbox/i }).click();
  await expect(page.getByText("Loaded the code")).toBeVisible();
  await page.getByRole("button", { name: "Verify email" }).click();
  await expect(page).toHaveURL(/login/);
  await page.waitForFunction(() => document.body.dataset.loginReady === "1");

  await page.getByLabel("Email").fill(CUSTOMER.email);
  await page.locator('input[name="password"]').fill(CUSTOMER.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/customer/);

  const authenticatorId = await addVirtualAuthenticator(page);
  expect(authenticatorId).toBeTruthy();

  await page.goto("/security");
  await expect(page.getByRole("heading", { name: "Security" })).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept("Test laptop key"));
  await page.getByRole("button", { name: "Register a passkey" }).click();
  await expect(page.getByText("Passkey registered")).toBeVisible();
  await expect(page.getByText("Test laptop key")).toBeVisible();

  // Log out via the API, then log back in with the passkey only.
  await apiLogout(page);
  await gotoLogin(page);
  await page.getByRole("button", { name: "Sign in with a passkey" }).click();
  await expect(page).toHaveURL(/\/customer/);
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();

  // The customer sees only their own records.
  const me = await page.request.get("/api/v1/auth/me");
  expect(me.ok()).toBeTruthy();
  const meBody = await me.json();
  expect(meBody.user.email).toBe(CUSTOMER.email);
  expect(meBody.user.role).toBe("customer");
  const extensions = await page.request.get("/api/v1/warranty/extensions/requests");
  expect(extensions.ok()).toBeTruthy();
  expect(await extensions.json()).toEqual([]);

  // Revoke with password confirmation, then the credential is dead.
  await page.goto("/security");
  page.once("dialog", (dialog) => dialog.accept(CUSTOMER.password));
  await page.getByRole("button", { name: "Revoke" }).click();
  await expect(page.getByText("Passkey revoked")).toBeVisible();

  await apiLogout(page);
  await gotoLogin(page);
  await page.getByRole("button", { name: "Sign in with a passkey" }).click();
  await expect(page.getByText("not recognized")).toBeVisible();
});
