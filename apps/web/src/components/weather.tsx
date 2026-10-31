"use client";
import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { advisoryTone } from "@/lib/intelligence";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge, TextField } from "@/components/ui";

type Advisory = components["schemas"]["AdvisoryResponse"];
type Forecast = components["schemas"]["ForecastResponse"];

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

function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `req-${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
}

export function WeatherOps() {
  const [siteId, setSiteId] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const availability = useGet<{ available: boolean; provider: string }>("/api/v1/weather/availability");
  const advisories = useGet<Advisory[]>(siteId.trim() ? `/api/v1/weather/advisories?site_id=${siteId.trim()}&status=open` : null);
  const [forecast, setForecast] = useState<Forecast | null>(null);

  async function saveGeolocation(verified: boolean) {
    if (!siteId.trim()) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api(`/api/v1/weather/sites/${siteId.trim()}/geolocation`, {
        method: "POST",
        body: JSON.stringify({ latitude: Number(lat), longitude: Number(lon), verified, source: "manual" }),
      });
      setMessage(verified ? "Coordinates verified for this site." : "Coordinates stored as unverified.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save coordinates.");
    } finally {
      setBusy(false);
    }
  }

  async function fetchForecast() {
    if (!siteId.trim()) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const body = await api<Forecast>("/api/v1/weather/forecasts", {
        method: "POST",
        body: JSON.stringify({ site_id: siteId.trim(), request_id: newRequestId() }),
      });
      setForecast(body);
      advisories.load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Forecast unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function actOnAdvisory(id: string, action: "acknowledge" | "dismiss") {
    setError(null);
    try {
      await api(`/api/v1/weather/advisories/${id}/ack`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      advisories.load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update the advisory.");
    }
  }

  return (
    <>
      <PageHeader
        title="Weather operations"
        description="Forecasts are advisory only. Acknowledging a warning never reschedules work — use the authorized scheduling flows."
      />
      {availability.data && !availability.data.available && (
        <Card className="mb-4">
          <p className="text-sm font-medium">Weather capability unavailable</p>
          <p className="mt-1 text-sm">No weather provider is configured, so forecasts are disabled rather than simulated.</p>
        </Card>
      )}
      <Card className="mb-4">
        <h2 className="font-semibold">Site location</h2>
        <div className="mt-2 grid gap-2 md:grid-cols-3">
          <TextField label="Site ID" value={siteId} onChange={(e) => setSiteId(e.target.value)} placeholder="Customer site UUID" />
          <TextField label="Latitude" value={lat} onChange={(e) => setLat(e.target.value)} placeholder="17.3850" />
          <TextField label="Longitude" value={lon} onChange={(e) => setLon(e.target.value)} placeholder="78.4867" />
        </div>
        <div className="mt-2 flex gap-2">
          <Button variant="secondary" onClick={() => saveGeolocation(false)} disabled={busy}>Store unverified</Button>
          <Button onClick={() => saveGeolocation(true)} disabled={busy}>Verify coordinates</Button>
          <Button variant="ghost" onClick={fetchForecast} disabled={busy || !siteId.trim()}>Fetch forecast</Button>
        </div>
        {message && <p className="mt-2 text-sm">{message}</p>}
        {error && <div className="mt-2"><ErrorState message={error} /></div>}
        {forecast && (
          <div className="mt-3 text-sm">
            <p><span className="font-medium">Provider:</span> {forecast.provider} · <span className="font-medium">Units:</span> {forecast.units} · <span className="font-medium">Freshness:</span> {forecast.freshness}</p>
            <p>Issued {forecast.issued_at} · valid {forecast.valid_from} to {forecast.valid_to}</p>
          </div>
        )}
      </Card>
      <h2 className="mb-2 font-semibold">Open advisories</h2>
      {!siteId.trim() && <EmptyState title="Pick a site" body="Enter a site ID above to list its weather advisories." />}
      {siteId.trim() && !advisories.data && !advisories.error && <LoadingState label="Loading advisories" />}
      {advisories.error && <ErrorState message={advisories.error} onRetry={advisories.load} />}
      <div className="space-y-3">
        {advisories.data?.map((item) => (
          <Card key={item.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold">{item.kind === "heavy_rain" ? "Heavy rain" : "High wind"} · {item.severity}</span>
              <StatusBadge status={advisoryTone(item.kind)} />
            </div>
            <p className="mt-1 text-sm">{item.summary}</p>
            <p className="mt-1 text-sm">Window: {item.window_from} to {item.window_to}</p>
            {(item.affected_appointments ?? []).length > 0 ? (
              <ul className="mt-1 list-disc pl-5 text-sm">
                {(item.affected_appointments ?? []).map((visit, index) => (
                  <li key={index}>{String((visit as Record<string, string>).kind)} {String((visit as Record<string, string>).reference)} at {String((visit as Record<string, string>).starts_at)}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-sm">No scheduled visits overlap this window.</p>
            )}
            <div className="mt-2 flex gap-2">
              <Button variant="secondary" onClick={() => actOnAdvisory(item.id, "acknowledge")}>Acknowledge</Button>
              <Button variant="ghost" onClick={() => actOnAdvisory(item.id, "dismiss")}>Dismiss</Button>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
