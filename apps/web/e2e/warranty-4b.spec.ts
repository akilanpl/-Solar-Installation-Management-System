import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const STAFF_PASSWORD = readFileSync("../../var/dev-seed-password.txt", "utf8").trim();
const CUSTOMER_PASSWORD = "Solarops123";

async function csrf(ctx: APIRequestContext): Promise<string> {
  const response = await ctx.get("/api/v1/auth/csrf");
  expect(response.status()).toBe(200);
  return ((await response.json()) as { csrf_token: string }).csrf_token;
}

async function apiLogin(ctx: APIRequestContext, kind: string, identifier: string, password: string) {
  const login = await ctx.post("/api/v1/auth/login", {
    headers: { "X-CSRF-Token": await csrf(ctx) },
    data: { account_kind: kind, identifier, password },
  });
  expect(login.status()).toBe(200);
}

async function post(ctx: APIRequestContext, url: string, data: unknown, key = false) {
  return ctx.post(url, {
    headers: {
      "X-CSRF-Token": await csrf(ctx),
      ...(key ? { "Idempotency-Key": randomUUID() } : {}),
    },
    data,
  });
}

async function patch(ctx: APIRequestContext, url: string, data: unknown) {
  return ctx.patch(url, {
    headers: { "X-CSRF-Token": await csrf(ctx) },
    data,
  });
}

async function signUpCustomer(page: Page, email: string, name: string) {
  // Warm the dev server first so on-demand route compiles never eat the navigation budget.
  await page.goto("/login");
  await page.waitForLoadState("load");
  await page.goto("/signup");
  await page.waitForLoadState("load");
  await page.getByLabel("Full name").fill(name);
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
}

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

type Ctx = { request: APIRequestContext };

async function installOrderAndTicket(
  c: APIRequestContext,
  s: APIRequestContext,
  w: APIRequestContext,
  t: APIRequestContext,
  sup: APIRequestContext,
  email: string,
  serial: string,
) {
  const enquiry = (await (await post(c, "/api/v1/enquiries", {
    contact_name: "Leela Nair", contact_phone: "9845099999", contact_email: email,
    site: { line1: "12 Lake View Road", city: "Hyderabad", state: "Telangana", postal_code: "500081" },
    preferred_capacity_w: 3000, grid_preference: "on_grid", monthly_bill_minor: 450000, subsidy_interest: true,
  }, true)).json()) as { id: string };
  expect((await patch(s, `/api/v1/enquiries/${enquiry.id}/qualification`, { status: "under_review", note: "Checking the roof." })).status()).toBe(200);
  expect((await patch(s, `/api/v1/enquiries/${enquiry.id}/qualification`, {
    status: "qualified", note: "Roof can take 3 kW.", shadow_free_area_sqm: "40.00", grid_connection_suitable: true,
  })).status()).toBe(200);
  const survey = (await (await post(s, "/api/v1/surveys", { enquiry_id: enquiry.id })).json()) as { id: string };
  const staff = (await (await sup.get("/api/v1/support/staff?role=technician")).json()) as { user_id: string; employee_code: string }[];
  const techId = staff.find((row) => row.employee_code === "EMP-TECH-001")?.user_id;
  expect(techId).toBeTruthy();
  expect((await post(s, `/api/v1/surveys/${survey.id}/assignment`, { technician_user_id: techId })).status()).toBe(200);
  expect((await post(t, `/api/v1/surveys/${survey.id}/start`, {})).status()).toBe(200);
  expect((await post(t, `/api/v1/surveys/${survey.id}/submission`, {
    azimuth_deg: "180.00", tilt_deg: "12.50", shadow_free_area_sqm: "38.25",
    cable_distance_m: "25.00", grid_connection: "suitable", notes: "South-facing roof.",
  })).status()).toBe(200);
  expect((await post(s, `/api/v1/surveys/${survey.id}/approval`, { decision: "approved", note: "Accepted." })).status()).toBe(200);
  const quote = (await (await post(s, "/api/v1/quotations", { survey_id: survey.id, package_code: "PKG-ONG-3", discount_minor: 0 }, true)).json()) as { id: string; total_minor: number };
  expect((await post(c, `/api/v1/quotations/${quote.id}/acceptance`, {})).status()).toBe(200);
  expect((await post(s, "/api/v1/payments/cash-receipts", {
    quotation_id: quote.id, amount_minor: quote.total_minor, receipt_reference: `CASH-4B-${Date.now()}`,
  }, true)).status()).toBe(201);
  const order = (await (await post(s, "/api/v1/orders", { quotation_id: quote.id }, true)).json()) as { id: string; reference: string };
  const detail = (await (await w.get(`/api/v1/orders/${order.id}`)).json()) as {
    lines: { component_code: string | null; quantity: number; line_kind: string }[];
  };
  const material = detail.lines.filter((line) => line.line_kind === "material" && line.component_code);
  expect(material.length).toBeGreaterThan(0);
  for (const line of material) {
    const op = (await (await post(w, "/api/v1/stock/operations", {
      operation_type: "receipt",
      lines: [{ component_code: line.component_code, quantity: `${line.quantity}.0000`, to_location: "MAIN" }],
    }, true)).json()) as { id: string };
    expect((await post(w, `/api/v1/stock/operations/${op.id}/ready`, {})).status()).toBe(200);
    expect((await post(w, `/api/v1/stock/operations/${op.id}/validate`, {})).status()).toBe(200);
  }
  const scanned = (await (await post(w, "/api/v1/serials/scan", { serial_number: serial, component_code: material[0].component_code })).json()) as { id: string };
  expect((await post(w, `/api/v1/serials/${scanned.id}/assign`, { order_id: order.id })).status()).toBe(200);
  const delivery = (await (await post(w, "/api/v1/deliveries", { order_id: order.id }, true)).json()) as { id: string };
  expect((await post(w, `/api/v1/deliveries/${delivery.id}/transit`, {})).status()).toBe(200);
  expect((await post(w, `/api/v1/deliveries/${delivery.id}/deliver`, {})).status()).toBe(200);
  expect((await post(w, `/api/v1/deliveries/${delivery.id}/confirm`, {})).status()).toBe(200);
  const ticket = (await (await post(c, "/api/v1/tickets", {
    order_id: order.id, serial_number: serial, fault_code: "E-07",
    symptoms: "The inverter shows fault code E-07 every afternoon and stops feeding power.",
    customer_urgency: "high", contact_preference: "phone",
  }, true)).json()) as { id: string; reference: string };
  expect((await post(sup, `/api/v1/tickets/${ticket.id}/triage`, {
    category: "inverter", verified_priority: "high", note: "Fault code points at the inverter.",
  })).status()).toBe(200);
  return { order, ticket, techId: techId as string, component: material[0].component_code as string };
}

async function publishPolicyAndPricing(
  a: APIRequestContext,
  code: string,
  version: Record<string, unknown>,
  parts: Record<string, number>,
) {
  const policy = (await (await post(a, "/api/v1/warranty/policies", {
    code, issuer: "SunPower works", category: "Inverter systems",
    description: "Browser acceptance cover for Phase 4B.",
  })).json()) as { id: string };
  const effective = new Date(Date.now() - 86400000).toISOString();
  expect((await post(a, `/api/v1/warranty/policies/${policy.id}/versions`, {
    duration_days: 730,
    applicable_components: [],
    covered_fault_categories: ["inverter"],
    covered_components: ["*"],
    covered_repair_types: ["repair", "replacement"],
    exclusions: { fault_categories: [], components: [] },
    labour_covered: true,
    replacement_allowed: true,
    replacement_continuation: "remainder",
    effective_from: effective,
    ...version,
  })).status()).toBe(201);
  expect((await post(a, "/api/v1/service-price-books", {
    label: `Browser rates ${code}`, labour_rates: { repair_labour: 6000 },
    part_prices: parts, effective_from: effective,
  })).status()).toBe(201);
  expect((await post(a, "/api/v1/service-tax-policies", {
    label: `Browser GST ${code}`, rate_bps: 1800, effective_from: effective,
  })).status()).toBe(201);
}

async function stockUnit(w: APIRequestContext, component: string, quantity: string) {
  const op = (await (await post(w, "/api/v1/stock/operations", {
    operation_type: "receipt",
    lines: [{ component_code: component, quantity, to_location: "MAIN" }],
  }, true)).json()) as { id: string };
  expect((await post(w, `/api/v1/stock/operations/${op.id}/ready`, {})).status()).toBe(200);
  expect((await post(w, `/api/v1/stock/operations/${op.id}/validate`, {})).status()).toBe(200);
}

async function recordRepair(
  ctx: APIRequestContext,
  support: APIRequestContext,
  techUserId: string,
  ticketId: string,
  minutes: number,
) {
  const job = (await (await post(support, `/api/v1/tickets/${ticketId}/repair-jobs`, {
    technician_user_id: techUserId, note: "Inverter specialist required.",
  }, true)).json()) as { id: string };
  expect((await post(ctx, `/api/v1/repair-jobs/${job.id}/arrival`, {})).status()).toBe(200);
  expect((await post(ctx, `/api/v1/repair-jobs/${job.id}/diagnostics`, {
    findings: "DC isolator contacts pitted; inverter itself healthy.",
    root_cause: "Worn isolator", readings: { voc_v: 612.5 },
  })).status()).toBe(200);
  const finished = new Date();
  const started = new Date(finished.getTime() - minutes * 60000);
  expect((await post(ctx, `/api/v1/repair-jobs/${job.id}/work`, {
    work_performed: "Replaced the DC isolator, retorqued terminals, verified generation.",
    work_started_at: started.toISOString(),
    work_finished_at: finished.toISOString(),
    parts_used: [{ component_code: "PANEL-550", quantity: 1 }],
  })).status()).toBe(200);
  expect((await post(ctx, `/api/v1/repair-jobs/${job.id}/submit`, {
    summary: "Isolator replaced and generation verified at 2.9 kW under load.",
  })).status()).toBe(200);
  return job;
}

async function apiCtx(browser: import("@playwright/test").Browser, kind: string, identifier: string, password: string) {
  const ctx = await browser.newContext();
  await apiLogin((await ctx.newPage()).request, kind, identifier, password);
  return ctx;
}

test("4B covered inverter fault: zero charge, immutable bill, confirmed resolution", async ({ page, browser }) => {
  test.setTimeout(300_000);
  const tag = `a${Date.now().toString().slice(-6)}`;
  const unit = tag.toUpperCase();
  const email = `leela.4b.${tag}@example.com`;
  const serial = `SN-4B-${unit}`;
  const contexts: import("@playwright/test").BrowserContext[] = [];
  try {
    await signUpCustomer(page, email, "Leela Nair");

    const customerApi = await apiCtx(browser, "customer", email, CUSTOMER_PASSWORD); contexts.push(customerApi);
    const salesApi = await apiCtx(browser, "employee", "EMP-SALES-001", STAFF_PASSWORD); contexts.push(salesApi);
    const warehouseApi = await apiCtx(browser, "employee", "EMP-WH-001", STAFF_PASSWORD); contexts.push(warehouseApi);
    const techApi = await apiCtx(browser, "employee", "EMP-TECH-001", STAFF_PASSWORD); contexts.push(techApi);
    const supportApi = await apiCtx(browser, "employee", "EMP-SUP-001", STAFF_PASSWORD); contexts.push(supportApi);
    const adminApi = await apiCtx(browser, "employee", "EMP-ADMIN-001", STAFF_PASSWORD); contexts.push(adminApi);
    const c = customerApi.request; const s = salesApi.request; const w = warehouseApi.request;
    const t = techApi.request; const sup = supportApi.request; const a = adminApi.request;

    await publishPolicyAndPricing(a, `INV4B-A-${tag}`, {}, { "PANEL-550": 1500000 });
    const { order, ticket, techId } = await installOrderAndTicket(c, s, w, t, sup, email, serial);
    expect((await post(sup, `/api/v1/warranty/orders/${order.id}/activate-coverages`, {})).status()).toBe(201);
    const decision = await (await post(sup, "/api/v1/warranty/coverage-decisions", {
      ticket_id: ticket.id, serial_number: serial,
    }, true)).json() as { verdict: string; reason: string };
    expect(decision.verdict).toBe("covered");
    await recordRepair(t, sup, techId, ticket.id, 90);

    const supportPage = await (await browser.newContext()).newPage();
    await signIn(supportPage, "support", "EMP-SUP-001", STAFF_PASSWORD);
    await expect(supportPage.getByRole("heading", { name: "Support inbox" })).toBeVisible({ timeout: 60000 });
    await supportPage.goto("/support/warranty");
    await expect(supportPage.getByRole("heading", { name: "Warranty intelligence" })).toBeVisible();
    await supportPage.getByLabel("Serial number", { exact: true }).fill(serial);
    await supportPage.getByRole("button", { name: "Look up" }).click();
    await expect(supportPage.getByText(`Coverage active`, { exact: false })).toBeVisible({ timeout: 30000 });

    await supportPage.goto("/support/estimates");
    await supportPage.getByLabel("Ticket ID").fill(ticket.id);
    await supportPage.getByRole("button", { name: "Build estimate" }).click();
    await expect(supportPage.getByText(/version 1 proposed/)).toBeVisible({ timeout: 30000 });
    const built = await (await sup.get(`/api/v1/tickets/${ticket.id}/estimates`)).json() as { id: string; reference: string }[];
    expect(built.length).toBe(1);

    await signIn(page, "customer", email, CUSTOMER_PASSWORD);
    await page.goto("/customer/equipment");
    await expect(page.getByText(serial).first()).toBeVisible({ timeout: 30000 });
    await page.goto("/customer/estimates");
    await page.getByRole("link", { name: new RegExp(built[0].reference) }).click();
    await expect(page.getByText("you pay ₹0.00").first()).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: "Accept this exact version" }).click();
    await expect(page.getByText(/authorized for this exact version/)).toBeVisible({ timeout: 30000 });

    const invoice = await (await post(sup, "/api/v1/service-invoices", { estimate_id: built[0].id }, true)).json() as {
      id: string; reference: string; status: string; customer_payable_minor: number; consumption_operation_id: string | null;
    };
    expect(["outstanding", "pending_payment"]).toContain(invoice.status);
    expect(invoice.customer_payable_minor).toBe(0);
    await stockUnit(w, "PANEL-550", "1.0000");
    const consumeResponse = await post(w, `/api/v1/service-invoices/${invoice.id}/consume`, {});
    expect(consumeResponse.status()).toBe(200);
    const consumed = (await consumeResponse.json()) as { consumption_operation_id: string | null };
    expect(consumed.consumption_operation_id).toBeTruthy();

    await page.goto("/customer/bills");
    await expect(page.getByText(invoice.reference).first()).toBeVisible({ timeout: 30000 });

    expect((await post(sup, `/api/v1/tickets/${ticket.id}/resolution-ready`, {
      summary: "Isolator replaced; generation verified at 2.9 kW under load.",
    })).status()).toBe(200);
    const summary = (await (await c.get(`/api/v1/tickets/${ticket.id}/resolution-summary`)).json()) as { summary_version: number };
    expect((await post(c, `/api/v1/tickets/${ticket.id}/confirmation`, {
      decision: "confirmed", summary_version: summary.summary_version,
    })).status()).toBe(200);
    expect((await post(sup, `/api/v1/tickets/${ticket.id}/close`, { reason: "Customer confirmed; closing the ticket." })).status()).toBe(200);

    const fresh = await browser.newContext();
    contexts.push(fresh);
    const freshPage = await fresh.newPage();
    await signIn(freshPage, "customer", email, CUSTOMER_PASSWORD);
    await freshPage.goto("/customer/complaints");
    await freshPage.getByRole("link", { name: ticket.reference }).click();
    await expect(freshPage.getByText("Status: Closed")).toBeVisible({ timeout: 30000 });
    const history = await (await freshPage.request.get(`/api/v1/tickets/${ticket.id}/history`)).json() as { action: string }[];
    for (const expected of ["created", "triaged", "resolution_ready", "resolution_confirmed", "closed"]) {
      expect(history.map((row) => row.action)).toContain(expected);
    }
    const decisions = await (await freshPage.request.get(`/api/v1/warranty/coverage-decisions?ticket_id=${ticket.id}`)).json() as { verdict: string }[];
    expect(decisions.map((row) => row.verdict)).toContain("covered");
  } finally {
    for (const ctx of contexts) await ctx.close();
  }
});

test("4B expired warranty: rejection blocks billing, accepted version bills exactly", async ({ page, browser }) => {
  test.setTimeout(300_000);
  const tag = `b${Date.now().toString().slice(-6)}`;
  const unit = tag.toUpperCase();
  const email = `leela.4b.${tag}@example.com`;
  const serial = `SN-4B-${unit}`;
  const contexts: import("@playwright/test").BrowserContext[] = [];
  try {
    await signUpCustomer(page, email, "Leela Nair");

    const customerApi = await apiCtx(browser, "customer", email, CUSTOMER_PASSWORD); contexts.push(customerApi);
    const salesApi = await apiCtx(browser, "employee", "EMP-SALES-001", STAFF_PASSWORD); contexts.push(salesApi);
    const warehouseApi = await apiCtx(browser, "employee", "EMP-WH-001", STAFF_PASSWORD); contexts.push(warehouseApi);
    const techApi = await apiCtx(browser, "employee", "EMP-TECH-001", STAFF_PASSWORD); contexts.push(techApi);
    const supportApi = await apiCtx(browser, "employee", "EMP-SUP-001", STAFF_PASSWORD); contexts.push(supportApi);
    const adminApi = await apiCtx(browser, "employee", "EMP-ADMIN-001", STAFF_PASSWORD); contexts.push(adminApi);
    const c = customerApi.request; const s = salesApi.request; const w = warehouseApi.request;
    const t = techApi.request; const sup = supportApi.request; const a = adminApi.request;

    await publishPolicyAndPricing(a, `INV4B-B-${tag}`, { duration_days: 30 }, { "PANEL-550": 1500000 });
    const { order, ticket, techId } = await installOrderAndTicket(c, s, w, t, sup, email, serial);
    expect((await post(sup, `/api/v1/warranty/orders/${order.id}/activate-coverages`, {})).status()).toBe(201);
    const late = new Date(Date.now() + 60 * 86400000).toISOString();
    const decision = await (await post(sup, "/api/v1/warranty/coverage-decisions", {
      ticket_id: ticket.id, serial_number: serial, evaluated_at: late,
    }, true)).json() as { verdict: string };
    expect(decision.verdict).toBe("not_covered");
    await recordRepair(t, sup, techId, ticket.id, 90);

    const built = await (await post(sup, `/api/v1/tickets/${ticket.id}/estimates`, {}, true)).json() as {
      id: string; reference: string; version: number; status: string;
      parts_minor: number; labour_minor: number; tax_minor: number;
      covered_minor: number; customer_payable_minor: number;
    };
    expect(built.version).toBe(1);
    expect(built.covered_minor).toBe(0);
    expect(built.customer_payable_minor).toBe(built.parts_minor + built.labour_minor + built.tax_minor);
    expect(built.customer_payable_minor).toBeGreaterThan(0);

    await signIn(page, "customer", email, CUSTOMER_PASSWORD);
    await page.goto(`/customer/estimates/${built.id}`);
    await page.getByLabel("Rejection reason (required)").fill("The price is too high; I want a second opinion.");
    await page.getByRole("button", { name: "Reject this version" }).click();
    await expect(page.getByText(/never authorizes billing/)).toBeVisible({ timeout: 30000 });

    const blocked = await post(sup, "/api/v1/service-invoices", { estimate_id: built.id }, true);
    expect(blocked.status()).toBe(409);

    const second = await (await post(sup, `/api/v1/tickets/${ticket.id}/estimates`, {}, true)).json() as { id: string; version: number };
    expect(second.version).toBe(2);
    await page.goto(`/customer/estimates/${second.id}`);
    await page.getByRole("button", { name: "Accept this exact version" }).click();
    await expect(page.getByText(/authorized for this exact version/)).toBeVisible({ timeout: 30000 });

    const invoice = await (await post(sup, "/api/v1/service-invoices", { estimate_id: second.id }, true)).json() as {
      id: string; reference: string; status: string;
      parts_minor: number; labour_minor: number; tax_minor: number;
      covered_minor: number; customer_payable_minor: number;
    };
    expect(["outstanding", "pending_payment"]).toContain(invoice.status);
    expect(invoice.covered_minor).toBe(0);
    expect(invoice.customer_payable_minor).toBe(invoice.parts_minor + invoice.labour_minor + invoice.tax_minor);
    await stockUnit(w, "PANEL-550", "1.0000");
    expect((await post(w, `/api/v1/service-invoices/${invoice.id}/consume`, {})).status()).toBe(200);

    await page.goto("/customer/bills");
    await expect(page.getByText(invoice.reference).first()).toBeVisible({ timeout: 30000 });

    expect((await post(sup, `/api/v1/tickets/${ticket.id}/resolution-ready`, {
      summary: "Out-of-warranty isolator replaced and billed at approved rates.",
    })).status()).toBe(200);
    const summary = (await (await c.get(`/api/v1/tickets/${ticket.id}/resolution-summary`)).json()) as { summary_version: number };
    expect((await post(c, `/api/v1/tickets/${ticket.id}/confirmation`, {
      decision: "confirmed", summary_version: summary.summary_version,
    })).status()).toBe(200);
    expect((await post(sup, `/api/v1/tickets/${ticket.id}/close`, { reason: "Customer confirmed; closing the ticket." })).status()).toBe(200);
    const detail = (await (await c.get(`/api/v1/tickets/${ticket.id}`)).json()) as { status: string };
    expect(detail.status).toBe("closed");
  } finally {
    for (const ctx of contexts) await ctx.close();
  }
});

test("4B replacement: custody chain, warranty transfer, quarantine inspection", async ({ page, browser }) => {
  test.setTimeout(300_000);
  const tag = `c${Date.now().toString().slice(-6)}`;
  const unit = tag.toUpperCase();
  const email = `leela.4b.${tag}@example.com`;
  const serial = `SN-4B-${unit}`;
  const replacementSerial = `SN-4B-R-${unit}`;
  const contexts: import("@playwright/test").BrowserContext[] = [];
  try {
    await signUpCustomer(page, email, "Leela Nair");

    const customerApi = await apiCtx(browser, "customer", email, CUSTOMER_PASSWORD); contexts.push(customerApi);
    const salesApi = await apiCtx(browser, "employee", "EMP-SALES-001", STAFF_PASSWORD); contexts.push(salesApi);
    const warehouseApi = await apiCtx(browser, "employee", "EMP-WH-001", STAFF_PASSWORD); contexts.push(warehouseApi);
    const techApi = await apiCtx(browser, "employee", "EMP-TECH-001", STAFF_PASSWORD); contexts.push(techApi);
    const supportApi = await apiCtx(browser, "employee", "EMP-SUP-001", STAFF_PASSWORD); contexts.push(supportApi);
    const adminApi = await apiCtx(browser, "employee", "EMP-ADMIN-001", STAFF_PASSWORD); contexts.push(adminApi);
    const c = customerApi.request; const s = salesApi.request; const w = warehouseApi.request;
    const t = techApi.request; const sup = supportApi.request; const a = adminApi.request;

    await publishPolicyAndPricing(a, `INV4B-C-${tag}`, {}, { "PANEL-550": 1500000 });
    const { order, ticket, techId } = await installOrderAndTicket(c, s, w, t, sup, email, serial);
    expect((await post(sup, `/api/v1/tickets/${ticket.id}/repair-jobs`, {
      technician_user_id: techId, note: "Replacement install required.",
    }, true)).status()).toBe(201);
    expect((await post(sup, `/api/v1/warranty/orders/${order.id}/activate-coverages`, {})).status()).toBe(201);
    const decision = await (await post(sup, "/api/v1/warranty/coverage-decisions", {
      ticket_id: ticket.id, serial_number: serial,
    }, true)).json() as { verdict: string };
    expect(decision.verdict).toBe("covered");

    const component = ((await (await w.get(`/api/v1/orders/${order.id}`)).json()) as {
      lines: { component_code: string | null; line_kind: string }[];
    }).lines.find((line) => line.line_kind === "material" && line.component_code)?.component_code;
    expect(component).toBeTruthy();
    const receipt = (await (await post(w, "/api/v1/stock/operations", {
      operation_type: "receipt",
      lines: [{ component_code: component, quantity: "1.0000", to_location: "MAIN" }],
    }, true)).json()) as { id: string };
    expect((await post(w, `/api/v1/stock/operations/${receipt.id}/ready`, {})).status()).toBe(200);
    expect((await post(w, `/api/v1/stock/operations/${receipt.id}/validate`, {})).status()).toBe(200);
    expect((await post(w, "/api/v1/serials/scan", {
      serial_number: replacementSerial, component_code: component,
    })).status()).toBe(201);

    const proposed = await (await post(sup, "/api/v1/replacements", {
      ticket_id: ticket.id, old_serial_number: serial, new_serial_number: replacementSerial,
    }, true)).json() as { id: string; reference: string; status: string };
    expect(proposed.status).toBe("proposed");

    const supportPage = await (await browser.newContext()).newPage();
    await signIn(supportPage, "support", "EMP-SUP-001", STAFF_PASSWORD);
    await supportPage.goto(`/support/replacements/${proposed.id}`);
    await expect(supportPage.getByRole("heading", { name: new RegExp(proposed.reference) })).toBeVisible({ timeout: 30000 });
    await supportPage.getByRole("button", { name: "Approve replacement" }).click();
    await expect(supportPage.getByText("approved", { exact: true })).toBeVisible({ timeout: 30000 });

    expect((await post(w, `/api/v1/replacements/${proposed.id}/reserve`, {})).status()).toBe(200);
    const issued = await (await post(w, `/api/v1/replacements/${proposed.id}/issue`, {}, true)).json() as { status: string };
    expect(issued.status).toBe("issued");
    const lookupNew = (await (await sup.get(`/api/v1/warranty/serials/lookup?serial_number=${replacementSerial}`)).json()) as { status: string };
    expect(lookupNew.status).toBe("installed");
    const lookupOld = (await (await sup.get(`/api/v1/warranty/serials/lookup?serial_number=${serial}`)).json()) as { status: string };
    expect(lookupOld.status).toBe("returned");

    const techPage = await (await browser.newContext()).newPage();
    await signIn(techPage, "technician", "EMP-TECH-001", STAFF_PASSWORD);
    await techPage.goto("/technician/install");
    await techPage.getByLabel("Replacement ID").fill(proposed.id);
    await techPage.getByRole("button", { name: "Confirm installation" }).click();
    await expect(techPage.getByText(/now the linked unit/)).toBeVisible({ timeout: 30000 });

    const warehousePage = await (await browser.newContext()).newPage();
    await signIn(warehousePage, "warehouse", "EMP-WH-001", STAFF_PASSWORD);
    await warehousePage.goto(`/warehouse/replacements/${proposed.id}`);
    await warehousePage.getByLabel("Returned-unit verdict").selectOption("quarantined");
    await warehousePage.getByLabel(/Inspection note/).fill(" returned unit held for bench review; contacts show heat damage. ");
    await warehousePage.getByRole("button", { name: "Record inspection" }).click();
    await expect(warehousePage.getByText(/Recorded inspection: quarantined/)).toBeVisible({ timeout: 30000 });

    const after = (await (await sup.get(`/api/v1/replacements/${proposed.id}`)).json()) as { status: string };
    expect(after.status).toBe("installed");
    const quarantined = (await (await sup.get(`/api/v1/warranty/serials/lookup?serial_number=${serial}`)).json()) as { status: string };
    expect(quarantined.status).toBe("quarantined");

    await signIn(page, "customer", email, CUSTOMER_PASSWORD);
    await page.goto("/customer/replacements");
    await expect(page.getByText(proposed.reference).first()).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(replacementSerial).first()).toBeVisible({ timeout: 30000 });
    const mine = (await (await c.get("/api/v1/warranty/serials/mine")).json()) as { serial_number: string | null }[];
    expect(mine.map((row) => row.serial_number)).toContain(replacementSerial);
  } finally {
    for (const ctx of contexts) await ctx.close();
  }
});
