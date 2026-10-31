# Phase 4D Weather and Generation

## Weather-aware operations

- Every forecast stores provider, `issued_at`, `fetched_at`,
  validity interval, units and the verbatim payload
  (`phase4d_forecast_snapshots`, idempotent on `request_id`).
- Forecasts run only for sites with **verified** coordinates
  (`phase4d_site_geolocations`); unverified/absent locations are
  rejected (422), never geocoded silently.
- No provider configured → `weather_unavailable` (503) and
  `{"available": false}`; the UI shows an honest unavailable banner.
  Forecasts are never simulated (tested).
- Advisories derive from stored forecasts only: heavy rain
  (peak ≥ 20 mm/h) and high wind (peak ≥ 17 m/s), each with severity,
  summary and window. Advisory history persists with status
  open → acknowledged/dismissed (re-action rejected 409).
- Each advisory lists affected **real** scheduled visits (surveys,
  installation jobs, repair jobs overlapping the window).
  Acknowledging never reschedules anything; appointment changes go
  through the authorized scheduling flows.
- Tested: stale forecasts labeled, missing coordinates, outage
  (timeout/HTTP/invalid JSON), invalid coordinates, region-agnostic
  thresholds, technician read access.

## Generation intelligence

Estimates and verified readings are kept strictly separate in every
response and on screen.

- Estimates (`pvest-v1`): capacity × monthly India-mean peak-sun-hours
  × performance ratio (0.7638 from documented soiling/temperature/
  inverter/wiring/mismatch losses) × orientation derate (documented
  linear rule clamped to [0.7, 1.0]) × scenario factor
  (0.9/1.0/1.1). Every response carries model, inputs, assumptions,
  interval and units, plus "planning estimate only, not measured
  generation". Example: 3 kW, January, expected, day ≈ 10.5 kWh.
- Verified readings: staff-only ingest (`support`/`admin`/`technician`;
  customers 403) with source, device ref, provider event ID, measured
  timestamp and Wh. Duplicates on `(device_ref, event_id)` return the
  original row (`duplicate: true`); negative values are quarantined;
  future/ancient timestamps are rejected with reasons. Rows are
  immutable; corrections arrive as new events.
- Empty state is explicit: "No authenticated device or provider
  readings exist for this order."
