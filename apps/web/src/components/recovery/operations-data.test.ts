import { describe, expect, it } from "vitest";
import { jobCompletion, profitBreakdown } from "./operations-data";

describe("recorded dashboard calculations", () => {
  it("keeps an empty workload distinct from measured zero completion", () => {
    expect(jobCompletion([])).toEqual({ complete: 0, total: 0, percent: null });
    const jobs = [{ status: "on_site" }, { status: "completed" }, { status: "cancelled" }] as Parameters<typeof jobCompletion>[0];
    expect(jobCompletion(jobs)).toEqual({ complete: 1, total: 3, percent: 33 });
  });
  it("preserves loss and incomplete reconciliation instead of inventing a margin", () => {
    const job = { revenue_minor: 10000, material_minor: 8000, labour_minor: 3000, expense_minor: 500,
      profit_minor: -1500, complete: false } as Parameters<typeof profitBreakdown>[0];
    expect(profitBreakdown(job)).toEqual({ revenue: 10000, cost: 11500, profit: -1500, complete: false });
  });
});
