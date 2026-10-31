import { describe, expect, it } from "vitest";
import { sourceBuildId } from "./build-id";
const SHA = "0123456789abcdef0123456789abcdef01234567";
describe("frontend source build identity", () => {
  it("is stable for the same actual source and public flags", () => {
    const env = { NEXT_PUBLIC_SOLAROPS_OFFLINE: "on", NEXT_PUBLIC_SOLAROPS_ENV: "development" };
    expect(sourceBuildId(SHA, env)).toBe(sourceBuildId(SHA + "\n", { ...env }));
    expect(sourceBuildId(SHA, env)).toMatch(new RegExp(`^${SHA}-[a-f0-9]{16}$`));
  });
  it("changes when a public security or offline build flag changes", () => {
    expect(sourceBuildId(SHA, {})).not.toBe(sourceBuildId(SHA, { NEXT_PUBLIC_SOLAROPS_PASSKEYS: "on" }));
    expect(sourceBuildId(SHA, {})).not.toBe(sourceBuildId(SHA, { NEXT_PUBLIC_SOLAROPS_OFFLINE: "on" }));
  });
  it("changes when source changes", () => {
    expect(sourceBuildId(SHA, {})).not.toBe(sourceBuildId("a".repeat(40), {}));
  });
  it("does not incorporate private runtime configuration", () => {
    expect(sourceBuildId(SHA, { DATABASE_URL: "private-one", SECRET_KEY: "secret-one" }))
      .toBe(sourceBuildId(SHA, { DATABASE_URL: "private-two", SECRET_KEY: "secret-two" }));
  });
  it("fails closed if the declared release source differs from Git HEAD", () => {
    expect(() => sourceBuildId(SHA, { SOLAROPS_RELEASE_SOURCE_SHA: "a".repeat(40) })).toThrow("does not match");
    expect(sourceBuildId(SHA, { SOLAROPS_RELEASE_SOURCE_SHA: SHA })).toBe(sourceBuildId(SHA, {}));
  });
  it("rejects missing or abbreviated source identities", () => {
    for (const invalid of ["", SHA.slice(0, 7), "z".repeat(40)]) expect(() => sourceBuildId(invalid, {})).toThrow("complete Git source SHA");
  });
});
