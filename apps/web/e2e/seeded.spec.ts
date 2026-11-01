import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

type DemoAccount = { identifier: string; password: string; role: string };

function account(email: string): DemoAccount {
  const path = process.env.SOLAROPS_E2E_CREDENTIALS_FILE;
  if (!path) throw new Error("Run the isolated browser runner with disposable credentials.");
  const accounts = JSON.parse(readFileSync(path, "utf8")) as Record<string, DemoAccount>;
  if (!accounts[email]) throw new Error("Run the local development demo seed before this test.");
  return accounts[email];
}

async function signIn(page: Page, email: string) {
  const demo = account(email);
  await page.goto("/login");
  await page.getByLabel("I am signing in as").selectOption(demo.role);
  await page.locator('input[name="identifier"]').fill(demo.identifier);
  await page.getByLabel("Password", { exact: true }).fill(demo.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}

test("seeded customer persists an enquiry, sales qualifies it, customer relogs and refreshes", async ({ page, browser }) => {
  test.setTimeout(120_000);
  const salesContext = await browser.newContext();
  const anonymous = await browser.newContext();
  try {
    expect((await anonymous.request.get("/api/v1/enquiries")).status()).toBe(401);
    await signIn(page, "customer.demo@solarops.example.com");
    await expect(page.getByRole("heading", { name: /Hello, Leela Nair/ })).toBeVisible();
    expect((await page.request.post("/api/v1/auth/logout")).status()).toBe(403);
    await page.getByRole("link", { name: "New enquiry", exact: true }).first().click();
    await page.getByLabel("Estimated monthly electricity bill (₹)").fill("6200");
    await page.getByLabel("Site address").fill("28 QA Rooftop Road");
    await page.getByLabel("City", { exact: true }).fill("Chennai");
    await page.getByLabel("State", { exact: true }).fill("Tamil Nadu");
    await page.getByLabel("PIN code").fill("600042");
    const createdResponse = page.waitForResponse((response) =>
      response.url().endsWith("/api/v1/enquiries") && response.request().method() === "POST");
    await page.getByRole("button", { name: "Submit enquiry" }).click();
    const created = await createdResponse;
    expect(created.status()).toBe(201);
    await expect(page).toHaveURL(/\/customer\/enquiries\/[0-9a-f-]+$/);
    const id = new URL(page.url()).pathname.split("/").at(-1);
    const persisted = await page.request.get(`/api/v1/enquiries/${id}`);
    expect(persisted.status()).toBe(200);
    const body = await persisted.json() as { id: string; reference: string };
    await expect(page.getByRole("heading", { name: body.reference, exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: body.reference, exact: true })).toBeVisible();

    const csrf = await (await page.request.get("/api/v1/auth/csrf")).json() as { csrf_token: string };
    const forbidden = await page.request.patch(`/api/v1/enquiries/${body.id}/qualification`, {
      headers: { "X-CSRF-Token": csrf.csrf_token }, data: { status: "qualified" },
    });
    expect(forbidden.status()).toBe(403);

    const sales = await salesContext.newPage();
    await signIn(sales, "sales.demo@solarops.example.com");
    await expect(sales.getByRole("heading", { name: "Enquiries", exact: true })).toBeVisible();
    await sales.getByRole("link", { name: body.reference, exact: true }).click();
    await sales.getByLabel("Next status").selectOption("qualified");
    await sales.getByLabel("Verified shadow-free roof area (m²)").fill("35");
    await sales.getByLabel("Grid connection suitability").selectOption("true");
    await sales.getByLabel(/^Note/).fill("QA demo: rooftop and customer details confirmed.");
    await sales.getByRole("button", { name: "Update status" }).click();
    const updateResponse = sales.waitForResponse((response) =>
      response.url().endsWith(`/api/v1/enquiries/${body.id}/qualification`) && response.request().method() === "PATCH");
    await sales.getByRole("button", { name: "Save status" }).click();
    expect((await updateResponse).status()).toBe(200);
    await expect(sales.getByText("Qualified", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Sign out", exact: true }).first().click();
    await expect(page.getByRole("heading", { name: "Sign in to SolarOps" })).toBeVisible();
    expect((await page.request.get("/api/v1/auth/me")).status()).toBe(401);
    await signIn(page, "customer.demo@solarops.example.com");
    await expect(page.getByRole("heading", { name: /Hello, Leela Nair/ })).toBeVisible();
    await page.goto(`/customer/enquiries/${body.id}`);
    await expect(page.getByText("Qualified", { exact: true })).toHaveCount(2);
    await page.reload();
    await expect(page.getByText("Qualified", { exact: true })).toHaveCount(2);
    const saved = await (await page.request.get(`/api/v1/enquiries/${body.id}`)).json();
    expect(saved.status).toBe("qualified");
    expect(saved.history.map((entry: { to_status: string }) => entry.to_status)).toEqual(["submitted", "qualified"]);
    expect(saved.history[1].actor_role).toBe("sales");
  } finally {
    await salesContext.close();
    await anonymous.close();
  }
});

test("seeded admin signs in through the normal employee flow", async ({ page }) => {
  await signIn(page, "admin.demo@solarops.example.com");
  await expect(page.getByRole("heading", { name: "Employees", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "EMP-SALES-DEMO-001", exact: true })).toBeVisible();
});
