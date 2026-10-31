import { describe, expect, it } from "vitest";

import {
  advisoryTone,
  generationAvailabilityLabel,
  snapshotFreshnessLabel,
} from "./intelligence";

describe("intelligence labels", () => {
  it("marks stale snapshots regardless of source", () => {
    expect(snapshotFreshnessLabel("cache", true)).toBe("Stale");
    expect(snapshotFreshnessLabel("cache", false)).toBe("Fresh (cache)");
    expect(snapshotFreshnessLabel("postgresql-fallback", false)).toBe("Live from database");
  });

  it("tones weather advisories as dangerous", () => {
    expect(advisoryTone("heavy_rain")).toBe("danger");
    expect(advisoryTone("high_wind")).toBe("danger");
    expect(advisoryTone("other")).toBe("secondary");
  });

  it("states verified-reading availability honestly", () => {
    expect(generationAvailabilityLabel(true, 0)).toBe("No verified readings yet");
    expect(generationAvailabilityLabel(false, 1)).toBe("1 verified reading");
    expect(generationAvailabilityLabel(false, 4)).toBe("4 verified readings");
  });
});
