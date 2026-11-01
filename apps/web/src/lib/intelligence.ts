export function snapshotFreshnessLabel(source: string, stale: boolean): string {
  if (stale) return "Stale";
  switch (source) {
    case "cache":
      return "Fresh (cache)";
    case "cache-rebuilt":
      return "Fresh (rebuilt)";
    case "cache-stale":
      return "Stale (rebuild failed)";
    case "postgresql-fallback":
      return "Live from database";
    default:
      return source;
  }
}

export function advisoryTone(kind: string): "danger" | "secondary" {
  return kind === "heavy_rain" || kind === "high_wind" ? "danger" : "secondary";
}

export function generationAvailabilityLabel(unavailable: boolean, count: number): string {
  if (unavailable) return "No verified readings yet";
  return `${count} verified reading${count === 1 ? "" : "s"}`;
}
