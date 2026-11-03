/** Fresh synthetic campaign. No routes mocked, no SQL business-state injection.
 * Browser UI: signup/verify/login, quote acceptance, work acknowledgment,
 * equipment, complaint, repair acceptance and persisted customer views.
 * Staff transitions: real authorized HTTP API with CSRF and idempotency.
 */
import { randomUUID } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

type Row = { id: string; reference: string; status: string; total_minor: number;
  is_test_only: boolean; starts_at: string; ends_at: string; summary_version: number; storage_key: string; code: string;
  user_id: string; employee_code: string; component_code: string; quantity: number;
  line_kind: string; requires_serial_tracking: boolean; serial_number: string;
  lines: Row[]; items: Row[]; components: Row[]; summary_hash: string };
const password = process.env.SOLAROPS_SEED_PASSWORD!;
const synthetic = 'Synthetic CI fixture: no physical field work or money movement is claimed.';
// Valid 2x2 PNG; synthetic evidence, never a claimed customer/site photograph.
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAC0lEQVR4nGNgQAYAAA4AAamRc7EAAAAASUVORK5CYII=', 'base64');
async function csrf(api: APIRequestContext) {
  const response = await api.get('/api/v1/auth/csrf');
  expect(response.status()).toBe(200);
  return (await response.json()).csrf_token as string;
}
async function command(api: APIRequestContext, path: string, data: unknown = {}, status = 200, method = 'POST'): Promise<Row> {
  const response = await api.fetch(`/api/v1${path}`, { method, data,
    headers: { 'X-CSRF-Token': await csrf(api), 'Idempotency-Key': randomUUID() } });
  expect(response.status(), `${method} ${path}: ${await response.text()}`).toBe(status);
  return await response.json() as Row;
}
async function read<T = Row>(api: APIRequestContext, path: string): Promise<T> {
  const response = await api.get(`/api/v1${path}`);
  expect(response.status(), path).toBe(200);
  return await response.json() as T;
}
async function upload(api: APIRequestContext, path: string): Promise<Row> {
  const response = await api.post(`/api/v1${path}`, { headers: { 'X-CSRF-Token': await csrf(api) },
    multipart: { upload: { name: 'synthetic-ci.png', mimeType: 'image/png', buffer: png } } });
  expect(response.status(), await response.text()).toBe(201);
  return await response.json() as Row;
}
async function login(page: Page, kind: string, identifier: string) {
  await page.goto('/login');
  await page.waitForFunction(() => document.body.dataset.loginReady === '1');
  await page.getByLabel('I am signing in as').selectOption(kind);
  await page.locator('input[name="identifier"]').fill(identifier);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login/);
}
async function signup(page: Page, email: string) {
  await page.goto('/signup');
  await page.getByLabel('Full name').fill('Synthetic CI Customer');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Mobile').fill('9845099999');
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/verify-email/);
  await page.getByRole('button', { name: 'Load code from local mailbox' }).click();
  await expect(page.getByText('Loaded the code from the local development mailbox.', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Verify email', exact: true }).click();
  await expect(page).toHaveURL(/login/);
  await login(page, 'customer', email);
}
async function audit(page: Page, name: string) {
  await expect(page.locator('main')).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: /Loading/i })).toHaveCount(0);
  // Measure settled content after finite entrance fades, not random opacity.
  // Infinite decorative animations remain enabled and are not awaited.
  await page.evaluate(async () => {
    await Promise.all(document.getAnimations().filter(animation =>
      animation.playState === 'running' && animation.effect?.getTiming().iterations !== Infinity
    ).map(animation => animation.finished.catch(() => undefined)));
  });
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  await test.info().attach(`${name}-axe`, { body: JSON.stringify(result), contentType: 'application/json' });
  expect(result.violations.filter(v => v.impact === 'critical' || v.impact === 'serious')).toEqual([]);
  for (const width of [390, 768, 1280]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await test.info().attach(`${name}-${width}`, { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' });
  }
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe('BODY');
}
async function uiMutation(page: Page, path: string, click: () => Promise<void>) {
  const response = page.waitForResponse(r => new URL(r.url()).pathname === `/api/v1${path}` && r.request().method() === 'POST');
  await click();
  const saved = await response;
  expect(saved.status(), await saved.text()).toBe(200);
}

test('fresh customer through delivered serials, acknowledged installation, active warranty and closed complaint', async ({ page, browser }) => {
  const tag = randomUUID().slice(0, 8);
  const email = `synthetic-ci-${tag}@example.com`;
  const failures: string[] = [];
  const contexts = [page.context()];
  function monitor(p: Page) {
    p.on('pageerror', error => failures.push(error.message));
    p.on('console', message => { if (message.type() === 'error' && !message.text().startsWith('Failed to load resource:')) failures.push(message.text()); });
    p.on('requestfailed', request => { if (request.failure()?.errorText !== 'net::ERR_ABORTED') failures.push(`${request.url()}: ${request.failure()?.errorText}`); });
    p.on('response', response => { if (response.status() >= 500) failures.push(`${response.status()} ${response.url()}`); });
  }
  monitor(page);
  try {
    await test.step('Fresh verified customer via browser', async () => {
      await signup(page, email); await audit(page, 'customer-home');
      const trigger = page.getByRole('button', { name: 'Accessibility', exact: true });
      await trigger.click();
      await page.getByRole('button', { name: 'Toggle Reading ruler', exact: true }).click();
      await expect(page.locator('.customer-reading-ruler')).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(trigger).toBeFocused();
      await page.reload();
      await expect(page.locator('.customer-reading-ruler')).toBeVisible();
      await trigger.click();
      await page.getByRole('button', { name: 'Toggle Reading ruler', exact: true }).click();
      await expect(page.locator('.customer-reading-ruler')).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Toggle Audio feedback', exact: true })).toBeVisible();
      await expect(page.getByRole('slider', { name: 'Reading speed' })).toBeVisible();
      await page.keyboard.press('Escape');
    });
    const staff: Record<string, Page> = {};
    for (const [role, code] of [['sales', 'SALES'], ['warehouse', 'WH'], ['technician', 'TECH'], ['support', 'SUP'], ['admin', 'ADMIN']]) {
      const context = await browser.newContext({ baseURL: 'http://127.0.0.1:3001', timezoneId: 'UTC' }); contexts.push(context);
      // Playwright Test starts tracing on every context, including manually created ones.
      staff[role] = await context.newPage(); monitor(staff[role]);
      await login(staff[role], role, `EMP-${code}-001`);
    }
    const c = page.request, s = staff.sales.request, w = staff.warehouse.request;
    const t = staff.technician.request, sup = staff.support.request, a = staff.admin.request;
    expect((await read<{ enabled: boolean }>(c, '/payments/razorpay/capability')).enabled).toBe(false);
    expect((await w.get('/api/v1/admin/employees')).status()).toBe(403);
    await command(s, '/stock/operations', { operation_type: 'receipt', lines: [{ component_code: 'PANEL-550', quantity: '1', to_location: 'MAIN' }] }, 403);
    await command(sup, '/warranty-policies', { component_code: 'PANEL-550', months: 24, activation_event: 'installation', terms: synthetic }, 403);
    const roster = await read<Row[]>(sup, '/support/staff?role=technician');
    const tech = roster.find(row => row.employee_code === 'EMP-TECH-001')!; expect(tech).toBeTruthy();
    for (const code of ['PANEL-550', 'INV-ONG']) await command(a, '/warranty-policies', {
      component_code: code, months: 24, activation_event: 'installation', terms: synthetic,
    });
    await command(a, `/scheduling/availability/${tech.user_id}`, {
      timezone: 'UTC', working_hours: Object.fromEntries(Array.from({ length: 7 }, (_, day) => [day, [['00:00', '23:59']]])),
      qualifications: { installation: '2099-12-31', survey: '2099-12-31' }, daily_capacity: 2,
    }, 200, 'PUT');
    const enquiry = await command(c, '/enquiries', {
      contact_name: 'Synthetic CI Customer', contact_phone: '9845099999', contact_email: email,
      site: { line1: 'Synthetic CI test site', city: 'Hyderabad', state: 'Telangana', postal_code: '500081' },
      preferred_capacity_w: 3000, grid_preference: 'on_grid', monthly_bill_minor: 450000, subsidy_interest: true,
    }, 201);
    await command(s, `/enquiries/${enquiry.id}/qualification`, { status: 'under_review', note: synthetic }, 200, 'PATCH');
    await command(s, `/enquiries/${enquiry.id}/qualification`, { status: 'qualified', note: synthetic,
      shadow_free_area_sqm: '40.00', grid_connection_suitable: true }, 200, 'PATCH');
    const survey = await command(s, '/surveys', { enquiry_id: enquiry.id }, 201);
    await command(s, `/surveys/${survey.id}/assignment`, { technician_user_id: tech.user_id });
    await command(t, `/surveys/${survey.id}/start`);
    await upload(t, `/surveys/${survey.id}/evidence`);
    await command(t, `/surveys/${survey.id}/submission`, { azimuth_deg: '180.00', tilt_deg: '12.50',
      shadow_free_area_sqm: '38.25', cable_distance_m: '25.00', grid_connection: 'suitable', notes: synthetic });
    await command(s, `/surveys/${survey.id}/approval`, { decision: 'approved', note: synthetic });
    const quote = await command(s, '/quotations', { survey_id: survey.id, package_code: 'PKG-ONG-3', discount_minor: 0 }, 201);
    await page.goto('/customer/quotations');
    await uiMutation(page, `/quotations/${quote.id}/acceptance`, () => page.getByRole('button', { name: /Accept version 1/ }).click());
    const payment = await command(c, '/payments/intents', { quotation_id: quote.id, amount_minor: quote.total_minor }, 201);
    expect(payment.is_test_only).toBe(true);
    const verified = await command(c, `/payments/intents/${payment.id}/sandbox-outcome`, { outcome: 'succeeded' });
    expect(verified.status).toBe('verified'); expect(verified.is_test_only).toBe(true);
    const replay = await command(c, `/payments/intents/${payment.id}/sandbox-outcome`, { outcome: 'succeeded' });
    expect(replay.id).toBe(payment.id); expect(replay.status).toBe('verified');
    await command(c, `/payments/intents/${payment.id}/sandbox-outcome`, { outcome: 'failed' }, 409);
    const order = await command(s, '/orders', { quotation_id: quote.id }, 201);
    await command(s, '/orders', { quotation_id: quote.id }, 409);
    await command(w, '/deliveries', { order_id: order.id }, 409); // No invented opening stock.
    const detail = await read(w, `/orders/${order.id}`);
    const catalogue = await read(w, '/workspace/warehouse-catalogue');
    const material = detail.lines.filter(line => line.line_kind === 'material' && line.component_code);
    expect(material.length).toBeGreaterThan(0);
    const serials: string[] = [];
    const unitLabels = new Map<string, string>();
    for (const line of material) {
      const receipt = await command(w, '/stock/operations', { operation_type: 'receipt', note: synthetic,
        lines: [{ component_code: line.component_code, quantity: String(line.quantity), to_location: 'MAIN' }] }, 201);
      await command(w, `/stock/operations/${receipt.id}/ready`);
      await command(w, `/stock/operations/${receipt.id}/validate`);
      if (catalogue.components.find(component => component.code === line.component_code)?.requires_serial_tracking) {
        const received: Row[] = [];
        for (let index = 0; index < line.quantity; index++) {
          const serial = `TEST-CI-${tag}-${line.component_code}-${index}`;
          const unit = await command(w, '/serials/scan', { serial_number: serial, component_code: line.component_code, operation_id: receipt.id }, 201);
          serials.push(unit.serial_number);
          unitLabels.set(unit.serial_number, `${line.component_code} · ${unit.serial_number}`);
          received.push(unit);
        }
        // Complete receipt reconciliation before reserving any physical unit.
        for (const unit of received) await command(w, `/serials/${unit.id}/assign`, { order_id: order.id });
      }
    }
    expect(serials).toHaveLength(7);
    await command(w, '/stock/allocations', { order_id: order.id,
      lines: material.map(line => ({ component_code: line.component_code, quantity: line.quantity, location_code: 'MAIN' })) });
    const delivery = await command(w, '/deliveries', { order_id: order.id }, 201);
    for (const action of ['transit', 'deliver', 'confirm']) await command(w, `/deliveries/${delivery.id}/${action}`);
    const slot = new Date(); slot.setUTCDate(slot.getUTCDate() + 1); slot.setUTCHours(12, 0, 0, 0);
    const job = await command(s, '/jobs', { order_id: order.id, technician_user_id: tech.user_id,
      slot_starts_at: slot.toISOString(), slot_ends_at: new Date(+slot + 3600000).toISOString() }, 201);
    await command(t, `/jobs/${job.id}/en-route`); await command(t, `/jobs/${job.id}/arrival`);
    await command(t, `/jobs/${job.id}/completion`, {}, 409);
    const mailbox = await read(c, `/dev/mailbox/${email}`); expect(mailbox.code).toMatch(/^\d{6}$/);
    await command(t, `/jobs/${job.id}/customer-otp`, { code: mailbox.code });
    const photo = await upload(t, `/jobs/${job.id}/uploads`);
    await command(t, `/jobs/${job.id}/evidence`, { photo_refs: [photo.storage_key], test_readings: { voc_v: 600 },
      installed_capacity_kw: '3.00', started_at: new Date(Date.now() - 120000).toISOString(), finished_at: new Date(Date.now() - 60000).toISOString() });
    await command(t, `/jobs/${job.id}/completion`, {}, 409); // OTP alone cannot accept work.
    await page.goto('/customer/installations');
    await page.getByRole('button', { name: 'Review work before acknowledging' }).click();
    for (const serial of serials) await expect(page.getByText(unitLabels.get(serial)!, { exact: true })).toBeVisible();
    await page.getByLabel('Your full name as acknowledgment').fill('Synthetic CI Customer');
    await uiMutation(page, `/jobs/${job.id}/signature`, () => page.getByRole('button', { name: 'I reviewed this work and accept it' }).click());
    expect((await command(t, `/jobs/${job.id}/completion`)).status).toBe('completed');
    const coverage = await read<Row[]>(c, `/orders/${order.id}/unit-warranties`);
    expect(coverage).toHaveLength(7);
    for (const unit of coverage) { expect(unit.status).toBe('active'); expect(+new Date(unit.ends_at)).toBeGreaterThan(+new Date(unit.starts_at)); }
    await page.goto('/customer/equipment');
    const equipment = page.getByRole('region', { name: 'Order-bound product warranties' });
    for (const serial of serials) await expect(equipment.getByText(serial, { exact: false })).toBeVisible();
    await audit(page, 'active-warranty');
    await page.goto('/customer/complaints');
    await page.getByLabel('Confirmed order', { exact: true }).selectOption(order.id);
    await page.getByLabel('Equipment serial (optional, must be installed on that order)', { exact: true }).fill(serials[0]);
    await page.getByLabel('What are the symptoms?').fill(`${synthetic} Synthetic inverter interruption for acceptance.`);
    const raised = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/tickets' && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Raise complaint' }).click();
    const raisedResponse = await raised; expect(raisedResponse.status()).toBe(201);
    const ticket = await raisedResponse.json() as Row;
    await command(sup, `/tickets/${ticket.id}/triage`, { category: 'inverter', verified_priority: 'normal', note: synthetic });
    const owners = await read<Row[]>(sup, '/support/staff?role=support');
    await command(sup, `/tickets/${ticket.id}/support-assignment`, { support_user_id: owners[0].user_id, note: synthetic });
    const repair = await command(sup, `/tickets/${ticket.id}/repair-jobs`, { technician_user_id: tech.user_id, note: synthetic }, 201);
    await command(t, `/repair-jobs/${repair.id}/arrival`);
    await command(t, `/repair-jobs/${repair.id}/diagnostics`, { findings: synthetic, root_cause: 'Synthetic test condition' });
    await command(t, `/repair-jobs/${repair.id}/work`, { work_performed: synthetic,
      work_started_at: new Date(Date.now() - 120000).toISOString(), work_finished_at: new Date(Date.now() - 60000).toISOString(), parts_used: [] });
    await upload(t, `/tickets/${ticket.id}/attachments?repair_job_id=${repair.id}`);
    expect((await command(t, `/repair-jobs/${repair.id}/submit`, { summary: synthetic })).status).toBe('work_submitted');
    await command(sup, `/tickets/${ticket.id}/resolution-ready`, { summary: synthetic });
    await page.goto(`/customer/complaints/${ticket.id}`);
    await expect(page.getByText('Repair summary (version 1)', { exact: false })).toBeVisible();
    await uiMutation(page, `/tickets/${ticket.id}/confirmation`, () => page.getByRole('button', { name: 'I reviewed this repair and accept it' }).click());
    expect((await command(sup, `/tickets/${ticket.id}/close`, { reason: synthetic })).status).toBe('closed');
    // New context/login tests persisted server state, rather than React state.
    const fresh = await browser.newContext({ baseURL: 'http://127.0.0.1:3001' }); contexts.push(fresh);
    const persisted = await fresh.newPage(); monitor(persisted); await login(persisted, 'customer', email);
    await persisted.goto(`/customer/complaints/${ticket.id}`);
    await expect(persisted.getByText('Status: Closed', { exact: false })).toBeVisible();
    await audit(persisted, 'closed-complaint');
    expect((await read(persisted.request, `/jobs/${job.id}`)).status).toBe('completed');
    expect(await read<Row[]>(persisted.request, `/orders/${order.id}/unit-warranties`)).toHaveLength(7);
    await persisted.goto('/customer/equipment');
    for (const serial of serials) await expect(persisted.getByRole('region', { name: 'Order-bound product warranties' }).getByText(serial, { exact: false })).toBeVisible();
    await persisted.reload();
    for (const serial of serials) await expect(persisted.getByRole('region', { name: 'Order-bound product warranties' }).getByText(serial, { exact: false })).toBeVisible();
    expect((await c.get('/api/v1/admin/employees')).status()).toBe(403);
    expect((await c.post('/api/v1/auth/logout')).status()).toBe(403); // Missing CSRF.
    const outsider = await browser.newContext({ baseURL: 'http://127.0.0.1:3001' }); contexts.push(outsider);
    const other = await outsider.newPage(); monitor(other); await signup(other, `synthetic-other-${tag}@example.com`);
    for (const path of [`/orders/${order.id}`, `/tickets/${ticket.id}`, `/jobs/${job.id}`, `/orders/${order.id}/unit-warranties`]) {
      expect((await other.request.get(`/api/v1${path}`)).status(), path).toBe(404);
    }
    await staff.sales.goto(`/sales/enquiries/${enquiry.id}`); await audit(staff.sales, 'sales-enquiry');
    await staff.technician.goto('/technician'); await audit(staff.technician, 'technician-completed');
    await staff.support.goto(`/support/tickets/${ticket.id}`); await audit(staff.support, 'support-closed');
    expect(failures).toEqual([]);
    writeFileSync(resolve(process.cwd(), '../../var/browser-ci/records.json'), JSON.stringify({
      enquiry: enquiry.id, survey: survey.id, quote: quote.id, order: order.id, delivery: delivery.id,
      installation: job.id, repair: repair.id, ticket: ticket.id, serials, payment: payment.id,
      provenance: synthetic, providerTesting: 'BLOCKED: legitimate Razorpay test credentials required',
    }, null, 2));
  } finally {
    for (const [index, context] of contexts.slice(1).entries()) {
      if (test.info().status !== test.info().expectedStatus) {
        for (const [pageIndex, opened] of context.pages().entries()) {
          if (!opened.isClosed()) await test.info().attach(`context-${index}-page-${pageIndex}-failure`, { body: await opened.screenshot({ fullPage: true }), contentType: 'image/png' });
        }
      }
      await context.close();
    }
  }
});
