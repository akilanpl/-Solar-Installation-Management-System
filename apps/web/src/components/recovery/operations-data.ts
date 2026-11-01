import type { components } from "@/generated/schema";

type Job = components["schemas"]["JobResponse"];
type Profit = components["schemas"]["JobProfit"];
export function jobCompletion(jobs: Job[]) {
  const complete = jobs.filter(job => job.status === "completed").length;
  return { complete, total: jobs.length, percent: jobs.length ? Math.round(complete / jobs.length * 100) : null };
}
export function profitBreakdown(job: Profit) {
  return { revenue: job.revenue_minor, cost: job.material_minor + job.labour_minor + job.expense_minor,
    profit: job.profit_minor, complete: job.complete };
}
