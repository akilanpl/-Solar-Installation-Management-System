// Scenarios C, D, E — offline technician, conflict/session expiry, warranty
// extension — against the isolated preview stack, with PostgreSQL spot
// checks after each meaningful transition.
import { execFileSync } from "child_process";
import { createHmac, randomUUID } from "crypto";
import { readFileSync } from "fs";
import { expect, test, type APIRequestContext, type Playwright } from "@playwright/test";

const TECH = { kind: "employee", identifier: "EMP-TECH-4E", password: "PreviewTech123" };
const SUPPORT = { kind: "employee", identifier: "EMP-SUP-4E", password: "PreviewSupport123" };
const ADMIN = { kind: "employee", identifier: "EMP-ADMIN-4E", password: "PreviewAdmin123" };
const SALES = { kind: "employee", identifier: "EMP-SALES-4E", password: "PreviewSales123" };
const WH = { kind: "employee", identifier: "EMP-WH-4E", password: "PreviewWh123" };

function psql(query: string): string {
  return execFileSync(
    "psql",
    ["-h", "127.0.0.1", "-U", "solarops", "-d", "solarops_4e_preview", "-tAc", query],
    { encoding: "utf-8", env: { ...process.env, PGPASSWORD: "solarops" } },
  ).trim();
}

function totp(secretBase32: string): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const char of secretBase32.replace(/=+$/, "").toUpperCase()) {
    bits += alphabet.indexOf(char).toString(2).padStart(5, "0");
  }
  const key = Buffer.from(bits.match(/.{1,8}/g)!.map((b) => parseInt(b, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const digest = createHmac("sha1", key).update(counter).digest();
  const o = digest[digest.length - 1] & 0x0f;
  const code = ((digest[o] & 0x7f) << 24) | (digest[o + 1] << 16) | (digest[o + 2] << 8) | digest[o + 3];
  return (code % 1_000_000).toString().padStart(6, "0");
}

class Api {
  private token: string | null = null;
  constructor(readonly ctx: APIRequestContext) {}

  async csrf(): Promise<string> {
    if (!this.token) {
      const response = await this.ctx.get("/api/v1/auth/csrf");
      expect(response.ok()).toBeTruthy();
      this.token = (await response.json()).csrf_token as string;
    }
    return this.token;
  }

  async rawPost(path: string, data: unknown, headers: Record<string, string> = {}) {
    return this.ctx.post(path, { data, headers });
  }

  async post(path: string, body: unknown, idem = false) {
    const headers: Record<string, string> = { "X-CSRF-Token": await this.csrf() };
    if (idem) headers["Idempotency-Key"] = randomUUID().replace(/-/g, "").slice(0, 16);
    const response = await this.ctx.post(path, { data: body, headers });
    if (!response.ok()) {
      throw new Error(`${path} -> ${response.status()} ${await response.text()}`);
    }
    return response.json();
  }

  async get(path: string) {
    const response = await this.ctx.get(path);
    if (!response.ok()) {
      throw new Error(`${path} -> ${response.status()} ${await response.text()}`);
    }
    return response.json();
  }

  async patch(path: string, body: unknown) {
    const response = await this.ctx.patch(path, {
      data: body,
      headers: { "X-CSRF-Token": await this.csrf() },
    });
    if (!response.ok()) {
      throw new Error(`${path} -> ${response.status()} ${await response.text()}`);
    }
    return response.json();
  }

  async login(kind: string, identifier: string, password: string, totpSecret?: string) {
    try {
      const body = await this.post("/api/v1/auth/login", {
        account_kind: kind, identifier, password,
      });
      if (body.mfa_required && body.ticket) {
        if (!totpSecret) throw new Error(`second factor required for ${identifier}`);
        return this.post("/api/v1/auth/mfa/ticket/verify-totp", {
          ticket: body.ticket, code: totp(totpSecret),
        });
      }
      return body;
    } finally {
      // Sign-in rotates the CSRF cookie; drop the cached token.
      this.token = null;
    }
  }

  async logout() {
    try {
      return await this.rawPost("/api/v1/auth/logout", {}, { "X-CSRF-Token": await this.csrf() });
    } finally {
      this.token = null;
    }
  }
}

async function signupCustomer(request: APIRequestContext, email: string) {
  const api = new Api(request);
  await api.post("/api/v1/auth/signup", {
    full_name: "Acceptance Customer",
    email,
    phone: "9845012345",
    password: "Acceptance123",
  });
  const mailbox = readFileSync("/tmp/solarops-4e-mailbox.jsonl", "utf-8").trim().split("\n");
  const mine = mailbox.reverse().find((line) => line.includes(email)) ?? "";
  const code = (mine.match(/code is (\d{6})/) ?? [])[1];
  expect(code).toBeTruthy();
  await api.post("/api/v1/auth/verify-email", { email, code });
  await api.login("customer", email, "Acceptance123");
  return api;
}

async function loginAs(pw: Playwright, who: { kind: string; identifier: string; password: string }) {
  const api = new Api(await pw.request.newContext({ baseURL: "http://localhost:3015" }));
  await api.login(who.kind, who.identifier, who.password);
  return api;
}

test("C+D offline sync, conflict, session expiry", async ({ request, playwright }) => {
  const stamp = Date.now();
  const customer = await signupCustomer(request, `accept-off-${stamp}@example.com`);
  const sales = await loginAs(playwright, SALES);
  const tech = await loginAs(playwright, TECH);
  await loginAs(playwright, SUPPORT);

  const enquiry = await customer.post("/api/v1/enquiries", {
    contact_name: "Acceptance Customer",
    contact_phone: "9845012345",
    contact_email: `accept-off-${stamp}@example.com`,
    site: { line1: "1 Test Road", city: "Hyderabad", state: "Telangana", postal_code: "500081" },
    preferred_capacity_w: 3000,
    grid_preference: "on_grid",
    monthly_bill_minor: 450000,
    subsidy_interest: false,
  }, true);
  await sales.patch(`/api/v1/enquiries/${enquiry.id}/qualification`, {
    status: "under_review", note: "Acceptance run.",
  });
  await sales.patch(`/api/v1/enquiries/${enquiry.id}/qualification`, {
    status: "qualified", note: "Roof can take a 3 kW system.",
    shadow_free_area_sqm: "40.00", grid_connection_suitable: true,
  });
  const survey = await sales.post("/api/v1/surveys", { enquiry_id: enquiry.id });
  const me = await tech.get("/api/v1/auth/me");
  await sales.post(`/api/v1/surveys/${survey.id}/assignment`, { technician_user_id: me.user.id });
  await tech.post(`/api/v1/surveys/${survey.id}/start`, {});

  // C: queue drafts offline, reconnect, sync exactly once.
  const assignments = await tech.get("/api/v1/offline/assignments");
  expect(assignments.surveys.map((item: { survey_id: string }) => item.survey_id)).toContain(
    survey.id,
  );
  expect(assignments.retention_days).toBe(7);
  const sync = await tech.post("/api/v1/offline/sync", {
    operations: [
      {
        op_type: "survey_draft", entity_type: "survey", entity_id: survey.id,
        client_operation_id: `wf-${stamp}-1`, base_field_version: 0,
        payload: { tilt_deg: 12.5, grid_connection: "suitable", notes: "Acceptance draft." },
      },
    ],
  });
  expect(sync.verdicts[0].status).toBe("applied");
  expect(sync.verdicts[0].result.field_version).toBe(1);
  const stored = await tech.get(`/api/v1/surveys/${survey.id}`);
  expect(stored.notes).toBe("Acceptance draft.");
  expect(
    psql(
      `SELECT count(*) FROM technician_sync_operations WHERE status='applied' AND entity_id='${survey.id}'`,
    ),
  ).toBe("1");

  // Idempotent retry of the same client operation id.
  const retry = await tech.post("/api/v1/offline/sync", {
    operations: [
      {
        op_type: "measurement", entity_type: "survey", entity_id: survey.id,
        client_operation_id: `wf-${stamp}-1`, base_field_version: 0,
        payload: { notes: "Tampered replay." },
      },
    ],
  });
  expect(retry.verdicts[0].status).toBe("applied");
  expect(retry.verdicts[0].duplicate).toBe(true);

  // D: stale version conflicts; an expired session is rejected, not faked.
  const stale = await tech.post("/api/v1/offline/sync", {
    operations: [
      {
        op_type: "survey_draft", entity_type: "survey", entity_id: survey.id,
        client_operation_id: `wf-${stamp}-2`, base_field_version: 0,
        payload: { notes: "Stale write." },
      },
    ],
  });
  expect(stale.verdicts[0].status).toBe("conflict");
  const refreshed = await tech.get(`/api/v1/surveys/${survey.id}`);
  expect(refreshed.notes).toBe("Acceptance draft.");

  const loggedOut = await tech.logout();
  expect(loggedOut.status()).toBe(204);
  const afterLogout = await tech.rawPost(
    "/api/v1/offline/sync",
    { operations: [] },
    { "X-CSRF-Token": await tech.csrf() },
  );
  expect(afterLogout.status()).toBe(401);
});

async function buildOrder(pw: Playwright, customer: Api, sales: Api, email: string) {
  const enquiry = await customer.post("/api/v1/enquiries", {
    contact_name: "Acceptance Customer", contact_phone: "9845012345", contact_email: email,
    site: { line1: "1 Test Road", city: "Hyderabad", state: "Telangana", postal_code: "500081" },
    preferred_capacity_w: 3000, grid_preference: "on_grid",
    monthly_bill_minor: 450000, subsidy_interest: false,
  }, true);
  await sales.patch(`/api/v1/enquiries/${enquiry.id}/qualification`, {
    status: "under_review", note: "Acceptance run.",
  });
  await sales.patch(`/api/v1/enquiries/${enquiry.id}/qualification`, {
    status: "qualified", note: "Roof can take a 3 kW system.",
    shadow_free_area_sqm: "40.00", grid_connection_suitable: true,
  });
  const survey = await sales.post("/api/v1/surveys", { enquiry_id: enquiry.id });
  const surveyTech = await loginAs(pw, TECH);
  const surveyor = await surveyTech.get("/api/v1/auth/me");
  await sales.post(`/api/v1/surveys/${survey.id}/assignment`, {
    technician_user_id: surveyor.user.id,
  });
  await surveyTech.post(`/api/v1/surveys/${survey.id}/start`, {});
  await surveyTech.post(`/api/v1/surveys/${survey.id}/submission`, {
    azimuth_deg: "180.00", tilt_deg: "12.50", shadow_free_area_sqm: "38.25",
    cable_distance_m: "25.00", grid_connection: "suitable", notes: "Acceptance survey.",
  });
  await sales.post(`/api/v1/surveys/${survey.id}/approval`, {
    decision: "approved", note: "Measurements accepted.",
  });
  const quote = await sales.post("/api/v1/quotations", {
    survey_id: survey.id, package_code: "PKG-ONG-3", discount_minor: 0,
  }, true);
  await customer.post(`/api/v1/quotations/${quote.id}/acceptance`, {});
  await sales.post("/api/v1/payments/cash-receipts", {
    quotation_id: quote.id, amount_minor: quote.total_minor,
    receipt_reference: `ACC-${Date.now()}`,
  }, true);
  return sales.post("/api/v1/orders", { quotation_id: quote.id }, true);
}

test("C2 repair-job queued mutation synchronizes exactly once", async ({ request, playwright }) => {
  const stamp = Date.now();
  const email = `accept-rep-${stamp}@example.com`;
  const customer = await signupCustomer(request, email);
  const sales = await loginAs(playwright, SALES);
  const tech = await loginAs(playwright, TECH);
  const support = await loginAs(playwright, SUPPORT);

  const order = await buildOrder(playwright, customer, sales, email);
  const ticket = await customer.post("/api/v1/tickets", {
    order_id: order.id, fault_code: "E-07",
    symptoms: "Acceptance offline ticket with enough detail to triage.",
    customer_urgency: "high", contact_preference: "phone",
  }, true);
  await support.post(`/api/v1/tickets/${ticket.id}/triage`, {
    category: "inverter", verified_priority: "high", note: "Acceptance triage.",
  });
  const me = await tech.get("/api/v1/auth/me");
  const job = await support.post(`/api/v1/tickets/${ticket.id}/repair-jobs`, {
    technician_user_id: me.user.id, note: "Acceptance repair.",
  }, true);

  const batched = await tech.post("/api/v1/offline/sync", {
    operations: [
      {
        op_type: "repair_diagnostics", entity_type: "repair", entity_id: job.id,
        client_operation_id: `wr-${stamp}-1`, base_field_version: 0,
        payload: { diagnostics: { findings: "Isolator pitted.", root_cause: "Wear" } },
      },
    ],
  });
  expect(batched.verdicts[0].status).toBe("applied");
  const detail = await tech.get(`/api/v1/repair-jobs/${job.id}`);
  expect(detail.diagnostics.findings).toBe("Isolator pitted.");
  expect(
    psql(`SELECT field_version FROM ticket_repair_jobs WHERE id='${job.id}'`),
  ).toBe("1");
});

test("E warranty extension pending until verified payment", async ({ request, playwright }) => {
  const stamp = Date.now();
  const email = `accept-ext-${stamp}@example.com`;
  const customer = await signupCustomer(request, email);
  const sales = await loginAs(playwright, SALES);
  const support = await loginAs(playwright, SUPPORT);
  const adminSecret = readFileSync("/tmp/solarops-4e-admin-totp.txt", "utf-8").trim();
  const admin = await (async () => {
    const api = new Api(await playwright.request.newContext({ baseURL: "http://localhost:3015" }));
    await api.login(ADMIN.kind, ADMIN.identifier, ADMIN.password, adminSecret);
    return api;
  })();
  const warehouse = await loginAs(playwright, WH);

  // Policy with a company-configured category.
  const policy = await admin.post("/api/v1/warranty/policies", {
    code: `EXT${String(stamp).slice(-7)}`, issuer: "Acceptance Works",
    category: "Inverter systems",
    description: "Acceptance policy for warranty extension scenario.",
  });
  const version = await admin.post(`/api/v1/warranty/policies/${policy.id}/versions`, {
    duration_days: 730, applicable_components: [], covered_fault_categories: ["inverter"],
    covered_components: ["*"], covered_repair_types: ["repair"],
    exclusions: { fault_categories: [], components: [] },
    effective_from: new Date(Date.now() - 86400000).toISOString(),
  });
  expect(version.version_number).toBe(1);

  // Order pipeline through confirmed delivery.
  const order = await buildOrder(playwright, customer, sales, email);
  const detail = await sales.get(`/api/v1/orders/${order.id}`);
  const materials = detail.lines.filter(
    (line: { component_code: string | null }) => line.component_code,
  );
  expect(materials.length).toBeGreaterThan(0);
  const material = materials[0];
  const receipt = await warehouse.post("/api/v1/stock/operations", {
    operation_type: "receipt",
    lines: materials.map(
      (line: { component_code: string; quantity: string | number }) => ({
        component_code: line.component_code,
        quantity: String(line.quantity),
        to_location: "MAIN",
      }),
    ),
  }, true);
  await warehouse.post(`/api/v1/stock/operations/${receipt.id}/ready`, {});
  await warehouse.post(`/api/v1/stock/operations/${receipt.id}/validate`, {});
  const serial = `SN-ACC-${stamp}`.slice(-16).toUpperCase();
  const scanned = await warehouse.post("/api/v1/serials/scan", {
    serial_number: serial, component_code: material.component_code,
  });
  await warehouse.post(`/api/v1/serials/${scanned.id}/assign`, { order_id: order.id });
  const delivery = await warehouse.post("/api/v1/deliveries", { order_id: order.id }, true);
  await warehouse.post(`/api/v1/deliveries/${delivery.id}/transit`, {});
  await warehouse.post(`/api/v1/deliveries/${delivery.id}/deliver`, {});
  await warehouse.post(`/api/v1/deliveries/${delivery.id}/confirm`, {});
  const activated = await support.post(`/api/v1/warranty/orders/${order.id}/activate-coverages`, {});
  expect(activated).toHaveLength(1);
  const coverage = activated[0];

  // Admin step-up with the preview-enrolled factor.
  const stepUp = await admin.post("/api/v1/auth/step-up/start", {});
  const granted = await admin.post("/api/v1/auth/step-up/verify-totp", {
    ticket: stepUp.ticket, code: totp(adminSecret),
  });
  const strong = { "X-Strong-Auth": granted.grant };

  const terms = await admin.ctx.post("/api/v1/warranty/extensions/terms", {
    data: {
      policy_id: policy.id, extension_days: 365, price_minor: 9000,
      currency: "INR", window_days: 90, eligible_categories: ["Inverter systems"],
      max_extensions: 1, requires_approval: true,
    },
    headers: { "X-CSRF-Token": await admin.csrf(), ...strong },
  });
  expect(terms.ok()).toBeTruthy();

  const eligibility = await customer.get(
    `/api/v1/warranty/extensions/eligibility?serial_number=${serial}`,
  );
  expect(eligibility.eligible).toBe(true);
  expect(eligibility.price_minor).toBe(9000);

  const requested = await customer.post("/api/v1/warranty/extensions/requests", {
    coverage_id: coverage.coverage_id, idempotency_key: `web-${stamp}`,
  });
  expect(requested.status).toBe("pending_approval");

  const approved = await admin.ctx.post(
    `/api/v1/warranty/extensions/requests/${requested.id}/approve`,
    {
      data: { note: "Documents verified." },
      headers: { "X-CSRF-Token": await admin.csrf(), ...strong },
    },
  );
  expect(approved.ok()).toBeTruthy();
  expect((await approved.json()).status).toBe("pending_payment");

  // Still pending: the coverage end date must not move on approval alone.
  const beforeActivate = psql(
    `SELECT ends_at::text FROM serialized_asset_coverage WHERE id='${coverage.coverage_id}'`,
  );
  const activatedRow = await admin.ctx.post(
    `/api/v1/warranty/extensions/requests/${requested.id}/activate`,
    {
      data: { payment_reference: "UPI-ACC-1" },
      headers: { "X-CSRF-Token": await admin.csrf(), ...strong },
    },
  );
  expect(activatedRow.ok()).toBeTruthy();
  expect((await activatedRow.json()).status).toBe("active");
  const afterActivate = psql(
    `SELECT ends_at::text FROM serialized_asset_coverage WHERE id='${coverage.coverage_id}'`,
  );
  expect(afterActivate).not.toBe(beforeActivate);
  expect(
    psql(`SELECT status FROM warranty_extensions WHERE id='${requested.id}'`),
  ).toBe("active");
  expect(
    psql(`SELECT count(*) FROM audit_events WHERE entity_type='warranty_extension'`),
  ).not.toBe("0");
});
