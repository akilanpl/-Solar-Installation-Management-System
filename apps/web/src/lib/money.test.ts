import { describe, expect, it } from "vitest";
import { formatPaise } from "./money";

describe("formatPaise", () => {
  it("formats rupees and paise in INR", () => {
    expect(formatPaise(0)).toBe("₹0.00");
    expect(formatPaise(17)).toBe("₹0.17");
    expect(formatPaise(12000)).toBe("₹120.00");
    expect(formatPaise(123456)).toBe("₹1,234.56");
  });

  it("keeps the sign outside the symbol", () => {
    expect(formatPaise(-250)).toBe("-₹2.50");
  });
});
