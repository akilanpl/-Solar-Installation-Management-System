/** Synthetic fixture inputs sent through real custody/installation guards. */
import { randomUUID } from "node:crypto";
import { expect, type APIRequestContext } from "@playwright/test";

export const syntheticPhoto = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAC0lEQVR4nGNgQAYAAA4AAamRc7EAAAAASUVORK5CYII=", "base64");
export async function fixtureCommand(api: APIRequestContext, path: string, data: unknown = {}, status = 200) {
  const csrf = await api.get("/api/v1/auth/csrf");
  expect(csrf.status()).toBe(200);
  const response = await api.post(`/api/v1${path}`, { data, headers: {
    "X-CSRF-Token": (await csrf.json()).csrf_token, "Idempotency-Key": randomUUID(),
  } });
  expect(response.status(), `${path}: ${await response.text()}`).toBe(status);
  return response.json();
}
export async function fixtureUpload(api: APIRequestContext, path: string) {
  const csrf = await api.get("/api/v1/auth/csrf");
  expect(csrf.status()).toBe(200);
  const response = await api.post(`/api/v1${path}`, { headers: { "X-CSRF-Token": (await csrf.json()).csrf_token },
    multipart: { upload: { name: "synthetic-fixture.png", mimeType: "image/png", buffer: syntheticPhoto } } });
  expect(response.status(), await response.text()).toBe(201);
  return response.json();
}
export async function receivedUnits(w: APIRequestContext, component: string, quantity: number, receiptId: string, firstSerial?: string) {
  const response = await w.get("/api/v1/workspace/warehouse-catalogue");
  expect(response.status()).toBe(200);
  const catalogue = await response.json() as { components: { code: string; requires_serial_tracking: boolean }[] };
  if (!catalogue.components.find(row => row.code === component)?.requires_serial_tracking) return [];
  const units: { id: string; serial_number: string }[] = [];
  for (let index = 0; index < quantity; index++) {
    const unit = await fixtureCommand(w, "/serials/scan", { component_code: component,
      operation_id: receiptId, serial_number: index === 0 && firstSerial ? firstSerial : `TEST-RELEASE-${randomUUID()}` }, 201);
    expect(unit.status).toBe("in_stock");
    units.push(unit);
  }
  return units;
}
export async function installReceivedOrder(c: APIRequestContext, s: APIRequestContext, t: APIRequestContext,
  orderId: string, techId: string, email: string) {
  const response = await s.get("/api/v1/scheduling/appointments");
  expect(response.status()).toBe(200);
  const appointments = await response.json() as { technician_user_id: string }[];
  const count = appointments.filter(row => row.technician_user_id === techId).length;
  const slot = new Date(Date.UTC(2030, 0, 7, 9 + count * 2));
  const job = await fixtureCommand(s, "/jobs", { order_id: orderId, technician_user_id: techId,
    slot_starts_at: slot.toISOString(), slot_ends_at: new Date(+slot + 3600000).toISOString() }, 201);
  const arrived = await fixtureCommand(t, `/jobs/${job.id}/arrival`);
  expect(arrived.arrival_at).toBeTruthy();
  const mailbox = await c.get(`/api/v1/dev/mailbox/${encodeURIComponent(email)}`);
  expect(mailbox.status()).toBe(200);
  await fixtureCommand(t, `/jobs/${job.id}/customer-otp`, { code: (await mailbox.json()).code });
  const photo = await fixtureUpload(t, `/jobs/${job.id}/uploads`);
  await fixtureCommand(t, `/jobs/${job.id}/evidence`, { photo_refs: [photo.storage_key], installed_capacity_kw: "3",
    test_readings: { voc_v: 612 }, started_at: arrived.arrival_at, finished_at: new Date().toISOString() });
  const summary = await c.get(`/api/v1/jobs/${job.id}/work-summary`);
  expect(summary.status()).toBe(200);
  await fixtureCommand(c, `/jobs/${job.id}/signature`, { signature_ref: "Synthetic release customer acknowledgment",
    customer_confirmed: true, summary_hash: (await summary.json()).summary_hash });
  const completed = await fixtureCommand(t, `/jobs/${job.id}/completion`);
  expect(completed.status).toBe("completed");
}
