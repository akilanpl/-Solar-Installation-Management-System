import { describe, expect, it } from "vitest";
import { newIdempotencyKey, ticketStatusLabel } from "./tickets";

describe("ticketStatusLabel", () => {
  it("labels every Phase 4A ticket state", () => {
    expect(ticketStatusLabel("open")).toBe("Open");
    expect(ticketStatusLabel("waiting_customer")).toBe("Waiting on you");
    expect(ticketStatusLabel("customer_confirmed")).toBe("Confirmed by you");
    expect(ticketStatusLabel("closed")).toBe("Closed");
  });

  it("passes unknown states through", () => {
    expect(ticketStatusLabel("mystery")).toBe("mystery");
  });
});

describe("newIdempotencyKey", () => {
  it("matches the API key alphabet", () => {
    expect(newIdempotencyKey()).toMatch(/^[A-Za-z0-9_-]{8,80}$/);
  });
});
