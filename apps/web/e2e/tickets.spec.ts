import { previewPassword } from "./preview-accounts";
import { randomUUID } from "node:crypto";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";


async function csrf(ctx: APIRequestContext): Promise<string> {
  const response = await ctx.get("/api/v1/auth/csrf");
  expect(response.status()).toBe(200);
  const body = (await response.json()) as { csrf_token: string };
  return body.csrf_token;
}

async function apiLogin(ctx: APIRequestContext, kind: string, identifier: string, password: string) {
  password = previewPassword(identifier, password);
  const login = await ctx.post("/api/v1/auth/login", {
    headers: { "X-CSRF-Token": await csrf(ctx) },
    data: { account_kind: kind, identifier, password },
  });
  expect(login.status()).toBe(200);
}

async function post(ctx: APIRequestContext, url: string, data: unknown, key = false) {
  const response = await ctx.post(url, {
    headers: {
      "X-CSRF-Token": await csrf(ctx),
      ...(key ? { "Idempotency-Key": randomUUID() } : {}),
    },
    data,
  });
  return response;
}

async function patch(ctx: APIRequestContext, url: string, data: unknown) {
  const response = await ctx.patch(url, {
    headers: { "X-CSRF-Token": await csrf(ctx) },
    data,
  });
  return response;
}

async function signIn(page: Page, kind: string, identifier: string, password: string) {
  password = previewPassword(identifier, password);
  await page.goto("/login");
  await page.getByLabel("I am signing in as").selectOption(kind);
  const idBox = page.locator('input[name="identifier"]');
  if (kind === "customer") {
    await page.getByLabel("Email").fill(identifier);
  } else {
    await idBox.fill(identifier);
  }
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}

test("Leela reports an inverter fault and confirms the repair in the browser", async ({ page, browser }) => {
  test.setTimeout(240_000);

  const email = `leela.e2e.${Date.now()}@example.com`;
  const serial = `SN-E2E-${Date.now().toString().slice(-6)}`;

  await page.goto("/signup");
  await page.getByLabel("Full name").fill("Leela Nair");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mobile").fill("9845099999");
  await page.getByLabel("Password").fill("Solarops123");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/verify-email*", { timeout: 30000 });
  await page.waitForLoadState("load");
  await expect(page.getByRole("heading", { name: "Verify your email" })).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "Load code from local mailbox" }).click();
  await expect(page.getByText("Loaded the code from the local development mailbox. This button is not available in production.", { exact: true })).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "Verify email" }).click();
  await page.waitForURL("**/login*", { timeout: 30000 });
  await page.waitForLoadState("load");
  await expect(page.getByRole("heading", { name: "Sign in to SolarOps" })).toBeVisible({ timeout: 30000 });
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("Solarops123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: /Hello, Leela Nair/ })).toBeVisible({ timeout: 30000 });

  const customerApi = await browser.newContext();
  const salesApi = await browser.newContext();
  const warehouseApi = await browser.newContext();
  const supportApi = await browser.newContext();
  await apiLogin((await supportApi.newPage()).request, "employee", "EMP-SUP-001", "");
  try {
    await apiLogin((await customerApi.newPage()).request, "customer", email, "Solarops123");
    const customer = await customerApi.newPage();
    const c = customer.request;
    const enquiry = await (await post(c, "/api/v1/enquiries", {
      contact_name: "Leela Nair", contact_phone: "9845099999", contact_email: email,
      site: { line1: "12 Lake View Road", city: "Hyderabad", state: "Telangana", postal_code: "500081" },
      preferred_capacity_w: 3000, grid_preference: "on_grid", monthly_bill_minor: 450000, subsidy_interest: true,
    }, true)).json() as { id: string };
    await apiLogin((await salesApi.newPage()).request, "employee", "EMP-SALES-001", "");
    const sales = await salesApi.newPage();
    const s = sales.request;
    expect((await patch(s, `/api/v1/enquiries/${enquiry.id}/qualification`, { status: "under_review", note: "Checking the roof." })).status()).toBe(200);
    expect((await patch(s, `/api/v1/enquiries/${enquiry.id}/qualification`, {
      status: "qualified", note: "Roof can take 3 kW.", shadow_free_area_sqm: "40.00", grid_connection_suitable: true,
    })).status()).toBe(200);
    const survey = await (await post(s, "/api/v1/surveys", { enquiry_id: enquiry.id })).json() as { id: string };
    const sup = (await supportApi.newPage()).request;
    const staff = await (await sup.get("/api/v1/support/staff?role=technician")).json() as { user_id: string; employee_code: string }[];
    const owners = await (await sup.get("/api/v1/support/staff?role=support")).json() as { user_id: string; employee_code: string }[];
    const ownerId = owners.find((row) => row.employee_code === "EMP-SUP-001")?.user_id;
    expect(ownerId).toBeTruthy();
    const techId = staff.find((row) => row.employee_code === "EMP-TECH-001")?.user_id;
    expect(techId).toBeTruthy();
    expect((await post(s, `/api/v1/surveys/${survey.id}/assignment`, { technician_user_id: techId })).status()).toBe(200);
    await apiLogin((await warehouseApi.newPage()).request, "employee", "EMP-WH-001", "");

    const techApi = await browser.newContext();
    await apiLogin((await techApi.newPage()).request, "employee", "EMP-TECH-001", "");
    const tech = await techApi.newPage();
    const t = tech.request;
    expect((await post(t, `/api/v1/surveys/${survey.id}/start`, {})).status()).toBe(200);
    expect((await post(t, `/api/v1/surveys/${survey.id}/submission`, {
      azimuth_deg: "180.00", tilt_deg: "12.50", shadow_free_area_sqm: "38.25",
      cable_distance_m: "25.00", grid_connection: "suitable", notes: "South-facing roof.",
    })).status()).toBe(200);
    expect((await post(s, `/api/v1/surveys/${survey.id}/approval`, { decision: "approved", note: "Accepted." })).status()).toBe(200);
    const quote = await (await post(s, "/api/v1/quotations", { survey_id: survey.id, package_code: "PKG-ONG-3", discount_minor: 0 }, true)).json() as { id: string; total_minor: number };
    expect((await post(c, `/api/v1/quotations/${quote.id}/acceptance`, {})).status()).toBe(200);
    expect((await post(s, "/api/v1/payments/cash-receipts", {
      quotation_id: quote.id, amount_minor: quote.total_minor, receipt_reference: `CASH-E2E-${Date.now()}`,
    }, true)).status()).toBe(201);
    const order = await (await post(s, "/api/v1/orders", { quotation_id: quote.id }, true)).json() as { id: string; reference: string };

    const warehouse = await warehouseApi.newPage();
    const w = warehouse.request;
    const detail = await (await w.get(`/api/v1/orders/${order.id}`)).json() as {
      lines: { component_code: string | null; quantity: number; line_kind: string }[];
    };
    const material = detail.lines.filter((line) => line.line_kind === "material" && line.component_code);
    expect(material.length).toBeGreaterThan(0);
    for (const line of material) {
      const op = await (await post(w, "/api/v1/stock/operations", {
        operation_type: "receipt",
        lines: [{ component_code: line.component_code, quantity: `${line.quantity}.0000`, to_location: "MAIN" }],
      }, true)).json() as { id: string };
      expect((await post(w, `/api/v1/stock/operations/${op.id}/ready`, {})).status()).toBe(200);
      expect((await post(w, `/api/v1/stock/operations/${op.id}/validate`, {})).status()).toBe(200);
    }
    const scanned = await (await post(w, "/api/v1/serials/scan", { serial_number: serial, component_code: material[0].component_code })).json() as { id: string };
    expect((await post(w, `/api/v1/serials/${scanned.id}/assign`, { order_id: order.id })).status()).toBe(200);
    const delivery = await (await post(w, "/api/v1/deliveries", { order_id: order.id }, true)).json() as { id: string };
    expect((await post(w, `/api/v1/deliveries/${delivery.id}/transit`, {})).status()).toBe(200);
    expect((await post(w, `/api/v1/deliveries/${delivery.id}/deliver`, {})).status()).toBe(200);
    expect((await post(w, `/api/v1/deliveries/${delivery.id}/confirm`, {})).status()).toBe(200);

    await page.goto("/customer/complaints");
    await page.getByLabel("Confirmed order").selectOption({ label: order.reference });
    await page.getByLabel(/Equipment serial/).fill(serial);
    await page.getByLabel(/Fault code/).fill("E-07");
    await page.getByLabel(/symptoms/).fill("The inverter shows fault code E-07 every afternoon and stops feeding power.");
    await page.getByLabel(/urgent does this feel/).selectOption("high");
    await page.getByRole("button", { name: "Raise complaint" }).click();
    await expect(page.getByText(/Complaint TKT-.* recorded/)).toBeVisible();
    const ticketLink = page.getByRole("link", { name: /TKT-/ }).first();
    await expect(ticketLink).toBeVisible();
    const ticketRef = (await ticketLink.textContent()) ?? "";
    await ticketLink.click();
    await expect(page.getByRole("heading", { name: `Complaint ${ticketRef.trim()}` })).toBeVisible();

    const supportPage = await (await browser.newContext()).newPage();
    await signIn(supportPage, "support", "EMP-SUP-001", "");
    await expect(supportPage.getByRole("heading", { name: "Support inbox" })).toBeVisible();
    await supportPage.getByRole("link", { name: ticketRef.trim(), exact: true }).click();
    await expect(supportPage.getByRole("heading", { name: `Ticket ${ticketRef.trim()}` })).toBeVisible();
    await supportPage.getByLabel("Category").selectOption("inverter");
    await supportPage.getByLabel("Verified priority").selectOption("high");
    await supportPage.getByLabel("Triage note").fill("Fault code points at the inverter.");
    await supportPage.getByRole("button", { name: "Triage ticket" }).click();
    await expect(supportPage.getByText("Saved.")).toBeVisible();
    await supportPage.getByLabel("Support owner").selectOption(ownerId as string);
    await supportPage.getByRole("button", { name: "Assign owner" }).click();
    await expect(supportPage.getByText("Saved.")).toBeVisible();
    await supportPage.getByLabel(/Repair technician/).selectOption(techId as string);
    await supportPage.getByRole("button", { name: "Create repair job" }).click();
    await expect(supportPage.getByText("Saved.")).toBeVisible();

    const techPage = await (await browser.newContext()).newPage();
    await signIn(techPage, "technician", "EMP-TECH-001", "");
    await techPage.waitForURL("**/technician*", { timeout: 30000 });
    await techPage.waitForLoadState("load");
    await techPage.goto("/technician/repairs");
    await expect(techPage.getByRole("heading", { name: "Repair assignments" })).toBeVisible();
    await techPage.getByRole("link", { name: /RPJ-/ }).first().click();
    await techPage.getByRole("button", { name: "Record arrival now" }).click();
    await expect(techPage.getByText("Saved.")).toBeVisible();
    await techPage.getByLabel(/Diagnostic findings/).fill("DC isolator contacts pitted; inverter itself healthy.");
    await techPage.getByRole("button", { name: "Save diagnostics" }).click();
    await expect(techPage.getByText("Saved.")).toBeVisible();
    await techPage.getByLabel(/Work performed/).fill("Replaced the DC isolator, retorqued terminals, verified generation.");
    await techPage.getByLabel("Work started").fill("2026-10-30T10:00");
    await techPage.getByLabel("Work finished").fill("2026-10-30T12:00");
    await techPage.getByRole("button", { name: "Save work" }).click();
    await expect(techPage.getByText("Saved.")).toBeVisible();
    await techPage.getByLabel(/Completion summary/).fill("Isolator replaced and generation verified at 2.9 kW under load.");
    await techPage.getByRole("button", { name: "Submit repair summary" }).click();
    await expect(techPage.getByText("Saved.")).toBeVisible();

    await supportPage.reload();
    await supportPage.getByLabel(/Resolution summary for the customer/).fill("Isolator replaced; generation verified at 2.9 kW under load.");
    await supportPage.getByRole("button", { name: "Mark resolution ready" }).click();
    await expect(supportPage.getByText("Saved.")).toBeVisible();

    await page.goto(`/customer/complaints`);
    await page.getByRole("link", { name: ticketRef.trim(), exact: true }).click();
    await expect(page.getByRole("heading", { name: /Repair summary/ })).toBeVisible();
    await expect(page.getByText("Isolator replaced; generation verified at 2.9 kW under load.").first()).toBeVisible();
    await page.getByRole("button", { name: "I reviewed this repair and accept it" }).click();
    await expect(page.getByText("Saved.")).toBeVisible();

    await supportPage.reload();
    await supportPage.getByLabel("Closure reason").fill("Customer confirmed; closing the ticket.");
    await supportPage.getByRole("button", { name: "Close ticket" }).click();
    await expect(supportPage.getByText("Saved.")).toBeVisible();
    await supportPage.reload();
    await expect(supportPage.getByText("Status: Closed")).toBeVisible();
    await page.reload();
    await expect(page.getByText("Status: Closed")).toBeVisible();

    const persisted = await page.request.get(`/api/v1/tickets`);
    expect(persisted.status()).toBe(200);
    const listed = (await persisted.json()) as { items: { reference: string; status: string }[] };
    expect(listed.items.map((row) => [row.reference, row.status])).toContainEqual([ticketRef.trim(), "closed"]);
  } finally {
    await customerApi.close();
    await salesApi.close();
    await warehouseApi.close();
    await supportApi.close();
  }
});
