import { describe, expect, it } from "vitest";

import { canAccessPath, destinationAfterLogin, homeForRole } from "./access";

describe("access", () => {
  it("sends each role to its own workspace", () => {
    expect(homeForRole("customer")).toBe("/customer");
    expect(homeForRole("sales")).toBe("/sales");
    expect(homeForRole("warehouse_staff")).toBe("/warehouse");
    expect(homeForRole("warehouse_manager")).toBe("/warehouse");
    expect(homeForRole("admin")).toBe("/admin");
  });

  it("does not let a customer open staff workspaces", () => {
    expect(canAccessPath("customer", "/sales")).toBe(false);
    expect(canAccessPath("customer", "/admin")).toBe(false);
    expect(canAccessPath("customer", "/customer/enquiries/new")).toBe(true);
  });

  it("ignores a requested admin path for a customer", () => {
    expect(destinationAfterLogin("customer", "/admin")).toBe("/customer");
    expect(destinationAfterLogin("sales", "/admin")).toBe("/sales");
    expect(destinationAfterLogin("admin", "/sales/enquiries/1")).toBe("/sales/enquiries/1");
  });

  it("rejects open redirects", () => {
    expect(destinationAfterLogin("customer", "https://evil.example")).toBe("/customer");
    expect(destinationAfterLogin("customer", "//evil.example")).toBe("/customer");
  });
});
