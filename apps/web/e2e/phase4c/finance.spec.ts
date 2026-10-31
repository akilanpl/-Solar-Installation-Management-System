import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const manifest = JSON.parse(
  fs.readFileSync(
    path.resolve("../../var/phase4c/acceptance-manifest.json"),
    "utf8",
  ),
);
const today = new Date().toISOString().slice(0, 10);
const dated = { posting_date: today, policy_id: manifest.policy_id };

async function login(
  page: Page,
  kind = "employee",
  identifier = "EMP-ADMIN-941",
  password = "Staffpass123",
) {
  await page.goto("/login");
  // Log in through the actual API using the browser's cookie jar, then exercise the finance UI.
  const csrf = await page.request.get("/api/v1/auth/csrf");
  const token = (await csrf.json()).csrf_token;
  const response = await page.request.post("/api/v1/auth/login", {
    headers: { "X-CSRF-Token": token },
    data: { account_kind: kind, identifier, password },
  });
  expect(response.status(), await response.text()).toBe(200);
}

async function command(
  page: Page,
  label: string,
  values: Record<string, string | number | boolean>,
) {
  await page
    .getByRole("combobox", { name: "Action", exact: true })
    .selectOption({ label });
  for (const [name, value] of Object.entries(values)) {
    const control = page.locator(`[name="${name}"]`);
    if (typeof value === "boolean") {
      await control.setChecked(value);
      continue;
    }
    const tag = await control.evaluate((el) => el.tagName.toLowerCase());
    if (tag === "select") await control.selectOption(String(value));
    else await control.fill(String(value));
  }
  await page.getByRole("button", { name: label, exact: true }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Recorded " }),
  ).toBeVisible();
}

async function rows(page: Page, kind: string) {
  const response = await page.request.get(
    `/api/v1/finance/records?kind=${kind}`,
  );
  expect(response.ok()).toBeTruthy();
  return response.json();
}

test("profitable and loss-making installations reconcile through real UI/API/PostgreSQL", async ({
  page,
}) => {
  await login(page);
  await page.goto("/admin/reports");
  await expect(
    page.getByRole("heading", { name: "Financial operations" }),
  ).toBeVisible();
  const before = await rows(page, "invoice");
  for (let i = 0; i < 2; i++) {
    const order = manifest.orders[i];
    let invoice = (await rows(page, "invoice")).find(
      (r: { payload: { source_id: string } }) =>
        r.payload.source_id === order.id,
    );
    if (!invoice) {
      await command(page, "Issue source invoice", {
        ...dated,
        source_kind: "order",
        source_id: order.id,
      });
      invoice = (await rows(page, "invoice")).find(
        (r: { payload: { source_id: string } }) =>
          r.payload.source_id === order.id,
      );
    }
    if (!(await rows(page, "receipt")).some((r:{payload:{payment_id:string}})=>r.payload.payment_id===manifest.payments[order.id])) {
      await command(page,"Reconcile verified cash",{...dated,order_id:order.id,payment_id:manifest.payments[order.id],invoice_id:invoice.id});
    }
    const recognitions = await rows(page, "recognition");
    if (
      !recognitions.some(
        (r: { payload: { invoice_id: string } }) =>
          r.payload.invoice_id === invoice.id,
      )
    )
      await command(page, "Recognize completed work", {
        ...dated,
        invoice_id: invoice.id,
        evidence_id: manifest.evidence_id,
      });
    for (const ledger of manifest.ledgers[order.id]) {
      if (
        (await rows(page, "material")).some(
          (r: { payload: { ledger_id: string } }) =>
            r.payload.ledger_id === ledger,
        )
      )
        continue;
      await command(page, "Record actual cost", {
        ...dated,
        order_id: order.id,
        kind: "material",
        ledger_id: ledger,
        amount_minor: i === 0 ? 100 : order.total_minor,
        evidence_id: manifest.evidence_id,
        description: "Synthetic evidenced actual cost",
        key: ledger,
      });
    }
    if (
      !(await rows(page, "completeness")).some(
        (r: { order_id: string }) => r.order_id === order.id,
      )
    )
      await command(page, "Attest cost completeness", {
        order_id: order.id,
        evidence_id: manifest.evidence_id,
        labour_complete: true,
        expenses_complete: true,
        note: "Synthetic labour and expense completeness reconciliation",
        key: `browser-complete-${i}`,
      });
  }
  const response = await page.request.get("/api/v1/finance/dashboard");
  const dashboard = await response.json();
  expect(
    dashboard.jobs.find(
      (j: { order_id: string }) => j.order_id === manifest.orders[0].id,
    ).profit_minor,
  ).toBeGreaterThan(0);
  expect(
    dashboard.jobs.find(
      (j: { order_id: string }) => j.order_id === manifest.orders[1].id,
    ).profit_minor,
  ).toBeLessThan(0);
  // The submitted timesheet on the profitable job must keep it incomplete until manager review.
  expect(
    dashboard.jobs.find(
      (j: { order_id: string }) => j.order_id === manifest.orders[1].id,
    ).complete,
  ).toBe(true);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Job profitability" }),
  ).toBeVisible();
  await expect(
    page.getByText(/Incomplete:.*unreviewed_timesheets/),
  ).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Export reconciled CSV" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("solarops-profit.csv");
  await page.screenshot({
    path: "../../var/phase4c/evidence/browser-profit.png",
    fullPage: true,
  });
  expect((await rows(page, "invoice")).length).toBeGreaterThanOrEqual(
    before.length,
  );
});

test("manager-approved technician payable is visibly unsettled and cash is unchanged", async ({
  page,
}) => {
  await login(page);
  await page.goto("/admin/reports");
  const before = await (
    await page.request.get("/api/v1/finance/dashboard")
  ).json();
  if (!(await rows(page, "timesheet_review")).length)
    await command(page, "Review timesheet", {
      ...dated,
      sheet_id: manifest.sheet_id,
      decision: "approved",
      approved_minutes: 60,
      note: "Synthetic manager approval; no transfer made",
      evidence_id: manifest.evidence_id,
    });
  const after = await (
    await page.request.get("/api/v1/finance/dashboard")
  ).json();
  expect(after.cash_minor).toBe(before.cash_minor);
  expect(after.payables_minor).toBe(6000);
  expect((await rows(page, "settlement")).length).toBe(0);
  await login(page, "employee", "EMP-TECH-901");
  await page.goto("/technician/labour");
  await expect(
    page.getByText("timesheet_review", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("₹60.00 unsettled", { exact: true }),
  ).toBeVisible();
  const records = await rows(page, "timesheet_review");
  expect(records[0].payload.settlement_state).toBe("unsettled");
  await page.getByRole("button", { name: records[0].id, exact: true }).click();
  await expect(page.locator("pre")).toContainText(
    '"settlement_state": "unsettled"',
  );
  await page.screenshot({
    path: "../../var/phase4c/evidence/browser-payable.png",
    fullPage: true,
  });
});

test("customer subsidy documents enforce checklist and sales review", async ({
  page,
}) => {
  await login(page, "customer", "leela@example.com", "Solarops123");
  await page.goto("/customer/subsidies");
  let cases = await rows(page, "subsidy_case");
  if (!cases.length) {
    await command(page, "Start subsidy application", {
      order_id: manifest.orders[0].id,
      scheme_id: manifest.scheme_id,
      consent_text: "I consent to this synthetic local document review",
      key: "browser-case",
    });
    cases = await rows(page, "subsidy_case");
  }
  const caseId = cases[0].id;
  await page.getByRole("button", { name: caseId, exact: true }).click();
  await expect(
    page.getByText(/Missing documents: electricity_bill, identity/),
  ).toBeVisible();
  for (const document_type of ["identity", "electricity_bill"]) {
    await page
      .locator('input[name="file"]')
      .setInputFiles({
        name: `synthetic-${document_type}.pdf`,
        mimeType: "application/pdf",
        buffer: Buffer.from("%PDF-1.4\nSYNTHETIC LOCAL DOCUMENT\n%%EOF"),
      });
    await page
      .getByRole("button", { name: "Upload evidence", exact: true })
      .click();
    const status = page.getByRole("status").filter({ hasText: "Evidence ID:" });
    await expect(status).toContainText("SHA-256:");
    const id = (await status.innerText()).match(
      /Evidence ID: ([a-f0-9-]+)/,
    )?.[1];
    expect(id).toBeTruthy();
    await command(page, "Attach subsidy document", {
      case_id: caseId,
      document_type,
      evidence_id: id!,
      key: `browser-${document_type}`,
    });
  }
  await page.getByRole("button", { name: caseId, exact: true }).click();
  await expect(page.getByText(/Missing documents: None/)).toBeVisible();
  await page.screenshot({
    path: "../../var/phase4c/evidence/browser-subsidy.png",
    fullPage: true,
  });
  await login(page, "employee", "EMP-SALES-901");
  await page.goto("/sales/subsidies");
  await page
    .locator('input[name="file"]')
    .setInputFiles({
      name: "review.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\nSYNTHETIC REVIEW ONLY\n%%EOF"),
    });
  await page
    .getByRole("button", { name: "Upload evidence", exact: true })
    .click();
  const status = page.getByRole("status").filter({ hasText: "Evidence ID:" });
  await expect(status).toContainText("SHA-256:");
  const ev = (await status.innerText()).match(/Evidence ID: ([a-f0-9-]+)/)?.[1];
  await command(page, "Review or record official decision", {
    case_id: caseId,
    action: "reviewed",
    note: "Synthetic checklist review complete",
    evidence_id: ev!,
    external_reference: "LOCAL-TEST-REVIEW",
    key: "browser-review",
  });
  const state = await (
    await page.request.get(`/api/v1/finance/subsidies/${caseId}`)
  ).json();
  expect(state.state).toBe("reviewed");
});

test("accepted Phase 4B bill becomes an immutable finance invoice", async ({
  page,
}) => {
  await login(page);
  await page.goto("/admin/reports");
  await command(page, "Issue source invoice", {
    ...dated,
    source_kind: "service_invoice",
    source_id: manifest.service_invoice.id,
  });
  const bills = await rows(page, "invoice");
  const bill = bills.find(
    (r: { payload: { source_id: string } }) =>
      r.payload.source_id === manifest.service_invoice.id,
  );
  expect(bill.payload.total_minor).toBe(
    manifest.service_invoice.customer_payable_minor,
  );
  expect(bill.payload.tax_minor).toBe(manifest.service_invoice.tax_minor);
  await page.getByRole("button", { name: bill.id, exact: true }).click();
  await expect(page.locator("pre").first()).toContainText(
    manifest.service_invoice.reference,
  );
  await page.screenshot({
    path: "../../var/phase4c/evidence/browser-service-invoice.png",
    fullPage: true,
  });
  const unauthorized = await page.request.patch(
    `/api/v1/finance/invoices/${bill.id}`,
    { data: { total_minor: 1 } },
  );
  expect([404, 405]).toContain(unauthorized.status());
});
