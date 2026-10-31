"use client";
import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { generationAvailabilityLabel } from "@/lib/intelligence";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, SelectField, StatusBadge } from "@/components/ui";

type OrderList = components["schemas"]["OrderList"];
type Estimate = components["schemas"]["GenerationEstimateResponse"];
type Summary = components["schemas"]["GenerationSummaryResponse"];
type Reading = components["schemas"]["ReadingResponse"];

function useGet<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    if (!path) return;
    setError(null);
    api<T>(path).then(setData).catch((e: Error) => setError(e.message));
  }, [path]);
  useEffect(load, [load]);
  return { data, error, load };
}

export function CustomerGeneration() {
  const orders = useGet<OrderList>("/api/v1/orders?page=1&page_size=50");
  const [orderId, setOrderId] = useState("");
  const [scenario, setScenario] = useState("expected");
  const [interval, setInterval] = useState("month");
  const summaryPath = orderId
    ? `/api/v1/generation/summary?order_id=${orderId}&scenario=${scenario}&interval=${interval}`
    : null;
  const summary = useGet<Summary>(summaryPath);
  const readingsPath = orderId ? `/api/v1/generation/readings?order_id=${orderId}` : null;
  const readings = useGet<Reading[]>(readingsPath);

  const estimate = summary.data?.estimate as Estimate | undefined;
  const inputs = ((estimate?.inputs ?? {}) as Record<string, string | number>);
  const assumptions = ((estimate?.assumptions ?? {}) as Record<string, string>);
  const verified = summary.data?.verified as
    | { reading_count: number; total_energy_kwh: number; latest_measured_at: string | null; latest_source: string | null; unavailable: boolean; unavailable_reason: string | null }
    | undefined;

  return (
    <>
      <PageHeader
        title="Solar generation"
        description="Planning estimates are clearly labeled and never counted as measured output. Verified readings appear only from authenticated devices."
      />
      {orders.error && <ErrorState message={orders.error} onRetry={orders.load} />}
      {!orders.data && !orders.error && <LoadingState label="Loading your orders" />}
      {orders.data && (
        <Card className="mb-4">
          <div className="grid gap-2 md:grid-cols-3">
            <SelectField label="Order" value={orderId} onChange={(e) => { setOrderId(e.target.value); }}>
              <option value="">Select an order</option>
              {orders.data.items.map((order) => (
                <option key={order.id} value={order.id}>{order.reference} · {order.package_code}</option>
              ))}
            </SelectField>
            <SelectField label="Scenario" value={scenario} onChange={(e) => setScenario(e.target.value)}>
              <option value="conservative">Conservative</option>
              <option value="expected">Expected</option>
              <option value="optimistic">Optimistic</option>
            </SelectField>
            <SelectField label="Interval" value={interval} onChange={(e) => setInterval(e.target.value)}>
              <option value="day">Day</option>
              <option value="month">Month</option>
              <option value="year">Year</option>
            </SelectField>
          </div>
          <div className="mt-2">
            <Button variant="secondary" onClick={() => { summary.load(); readings.load(); }} disabled={!orderId}>
              Recalculate
            </Button>
          </div>
        </Card>
      )}
      {summary.error && <div className="mb-4"><ErrorState message={summary.error} onRetry={summary.load} /></div>}
      {estimate && (
        <Card className="mb-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold">Estimate · {estimate.energy_kwh} {estimate.unit} / {estimate.interval}</h2>
            <StatusBadge status="estimate" />
          </div>
          <p className="mt-1 text-sm">Model {estimate.model} · scenario {estimate.scenario} · month {estimate.month}</p>
          <p className="mt-1 text-sm">
            {inputs.capacity_w} W · {inputs.peak_sun_hours_per_day} peak sun hours/day · performance
            ratio {inputs.performance_ratio} · orientation factor {inputs.orientation_factor}
          </p>
          <p className="mt-1 text-sm">Basis: {assumptions.irradiation}. {assumptions.note}</p>
        </Card>
      )}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">Verified generation</h2>
          {verified && <StatusBadge status={generationAvailabilityLabel(verified.unavailable, verified.reading_count)} />}
        </div>
        {verified?.unavailable && (
          <p className="mt-2 text-sm">{verified.unavailable_reason}</p>
        )}
        {verified && !verified.unavailable && (
          <>
            <p className="mt-1 text-sm">
              Total {verified.total_energy_kwh} kWh across {verified.reading_count} readings.
              Latest: {verified.latest_measured_at ?? "—"} via {verified.latest_source ?? "—"}.
            </p>
            {!readings.data && !readings.error && <div className="mt-2"><LoadingState label="Loading readings" /></div>}
            {readings.data && readings.data.length > 0 && (
              <table className="mt-2 w-full text-sm">
                <thead>
                  <tr className="text-left">
                    <th className="py-1 pr-2">Measured at</th>
                    <th className="py-1 pr-2">Energy (Wh)</th>
                    <th className="py-1 pr-2">Device</th>
                    <th className="py-1 pr-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {readings.data.map((row) => (
                    <tr key={row.id} className="border-t border-moss-100">
                      <td className="py-1 pr-2">{row.measured_at}</td>
                      <td className="py-1 pr-2">{String(row.energy_wh)}</td>
                      <td className="py-1 pr-2">{row.device_ref}</td>
                      <td className="py-1 pr-2">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
        {!orderId && <div className="mt-2"><EmptyState title="No order selected" body="Choose one of your orders to see its generation estimate and verified readings." /></div>}
      </Card>
    </>
  );
}
