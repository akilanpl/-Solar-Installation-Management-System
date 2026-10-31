import { expect, test, type Page } from "@playwright/test";

const CUSTOMER_PASSWORD = "Solarops123";
const SUPPORT_ID = "EMP-SUP-4D";
const SUPPORT_PASSWORD = "Support4d123";

async function signIn(page: Page, kind: string, identifier: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("I am signing in as").selectOption(kind);
  if (kind === "customer") {
    await page.getByLabel("Email").fill(identifier);
  } else {
    await page.getByLabel("Employee ID").fill(identifier);
  }
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL(`**/${kind}*`, { timeout: 60000 });
  await page.waitForLoadState("load");
}

test("support intelligence workspace loads, rejects unknown snapshots, drafts assists", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));

  await signIn(page, "support", SUPPORT_ID, SUPPORT_PASSWORD);

  await page.goto("/support/intelligence");
  await expect(page.getByRole("heading", { name: "Customer intelligence" })).toBeVisible({ timeout: 60000 });

  await page.getByLabel("Customer user ID").fill("00000000-0000-0000-0000-000000000000");
  await page.getByRole("button", { name: "Load snapshot" }).click();
  await expect(page.getByText("No customer profile for this user.", { exact: false })).toBeVisible({ timeout: 60000 });

  await page.getByLabel(/Customer complaint/).fill("The inverter shows E-07 every afternoon and stops feeding power.");
  await page.getByRole("button", { name: "Generate supervised draft" }).click();
  await expect(page.getByText("Deterministic assistance", { exact: false })).toBeVisible({ timeout: 60000 });
  await expect(page.getByText("E-07", { exact: false }).first()).toBeVisible({ timeout: 60000 });
  await page.getByRole("button", { name: "Discard" }).click();
  await expect(page.getByText("discarded", { exact: false }).first()).toBeVisible({ timeout: 60000 });

  expect(errors).toEqual([]);
});

test("weather operations show the honest unavailable state", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));

  await signIn(page, "support", SUPPORT_ID, SUPPORT_PASSWORD);

  await page.goto("/support/weather");
  await expect(page.getByRole("heading", { name: "Weather operations" })).toBeVisible({ timeout: 60000 });
  await expect(page.getByText("Weather capability unavailable", { exact: false })).toBeVisible({ timeout: 60000 });

  expect(errors).toEqual([]);
});

test("customer generation workspace renders with honest empty state", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));

  const email = `gen4d-${Date.now()}@example.com`;
  await page.goto("/login");
  await page.waitForLoadState("load");
  await page.goto("/signup");
  await page.waitForLoadState("load");
  await page.getByLabel("Full name").fill("Gen Customer");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mobile").fill("9845099999");
  await page.getByLabel("Password").fill(CUSTOMER_PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/verify-email*", { timeout: 60000 });
  await page.waitForLoadState("load");
  await page.getByRole("button", { name: "Load code from local mailbox" }).click();
  await expect(page.getByText("Loaded the code from the local development mailbox.", { exact: false })).toBeVisible({ timeout: 60000 });
  await page.getByRole("button", { name: "Verify email" }).click();
  await page.waitForURL("**/login*", { timeout: 60000 });
  await page.waitForLoadState("load");

  await signIn(page, "customer", email, CUSTOMER_PASSWORD);

  await page.goto("/customer/generation");
  await expect(page.getByRole("heading", { name: "Solar generation" })).toBeVisible({ timeout: 60000 });
  await expect(page.getByText("No order selected", { exact: false })).toBeVisible({ timeout: 60000 });

  expect(errors).toEqual([]);
});
