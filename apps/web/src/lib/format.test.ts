import { describe, expect, it } from "vitest";

import { formatCapacity, formatInrFromPaise, rupeesToPaise } from "./format";

describe("money and capacity formatting", () => {
  it("converts whole rupees to integer paise", () => {
    expect(rupeesToPaise("4500")).toBe(450000);
    expect(rupeesToPaise("0")).toBe(0);
    expect(rupeesToPaise("12.5")).toBeNull();
    expect(rupeesToPaise("-1")).toBeNull();
  });

  it("formats paise without binary floating point", () => {
    expect(formatInrFromPaise(450000)).toBe("₹4,500.00");
    expect(formatInrFromPaise(10)).toBe("₹0.10");
  });

  it("shows capacity in kilowatts", () => {
    expect(formatCapacity(3000)).toBe("3 kW");
  });
});
