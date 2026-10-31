import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";

const PUBLIC_FLAGS = [
  "NEXT_PUBLIC_SOLAROPS_ENV",
  "NEXT_PUBLIC_SOLAROPS_OFFLINE",
  "NEXT_PUBLIC_SOLAROPS_PASSKEYS",
] as const;

/** Identifies source and explicitly public build-time behavior without exposing config. */
export function sourceBuildId(head: string, env: Record<string, string | undefined>): string {
  const sha = head.trim().toLowerCase();
  if (!/^[0-9a-f]{40}$/.test(sha)) throw new Error("A complete Git source SHA is required for the frontend build.");
  const declared = env.SOLAROPS_RELEASE_SOURCE_SHA;
  if (declared && declared.toLowerCase() !== sha) {
    throw new Error("SOLAROPS_RELEASE_SOURCE_SHA does not match the frontend Git HEAD.");
  }
  const flags = PUBLIC_FLAGS.map(name => [name, env[name] ?? ""]);
  const digest = createHash("sha256").update(JSON.stringify(flags)).digest("hex").slice(0, 16);
  return `${sha}-${digest}`;
}

export function currentSourceBuildId(cwd: string, env: Record<string, string | undefined>): string {
  const sha = execFileSync("git", ["-C", cwd, "rev-parse", "--verify", "HEAD"], {
    encoding: "utf8", stdio: ["ignore", "pipe", "pipe"],
  });
  return sourceBuildId(sha, env);
}
