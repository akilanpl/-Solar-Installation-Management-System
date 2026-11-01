import { decimalRupeesToPaise } from "./format";
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


describe("decimal INR receipt amounts", () => {
  it.each([["0",0],["0.01",1],["12.3",1230],["12.34",1234],["1000000",100000000]])("converts %s exactly", (input, expected) => {
    expect(decimalRupeesToPaise(String(input))).toBe(expected);
  });
  it.each(["-1","NaN","1.001","1e3","1000000.01",""])("rejects %s", input => {
    expect(decimalRupeesToPaise(input)).toBeNull();
  });
});
