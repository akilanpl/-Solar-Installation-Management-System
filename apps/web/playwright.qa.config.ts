import { defineConfig } from "@playwright/test";

import base from "./playwright.config";

const database = process.env.SOLAROPS_E2E_DATABASE_URL;
if (!database) throw new Error("Use apps/api/scripts/run_browser_qa.py to prepare isolated browser QA.");
const target = new URL(database);
if (target.pathname !== "/solarops_test" || !["127.0.0.1", "localhost"].includes(target.hostname)) {
  throw new Error("Browser QA requires local solarops_test; development databases are forbidden.");
}

export default defineConfig({
  ...base,
  use: { ...base.use, baseURL: "http://127.0.0.1:3001" },
  webServer: [
    {
      command: "cd ../api && uv run uvicorn app.main:app --host 127.0.0.1 --port 8001",
      url: "http://127.0.0.1:8001/api/v1/ready",
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        SOLAROPS_APP_ENV: "development",
        SOLAROPS_DATABASE_URL: database,
        SOLAROPS_COOKIE_SECURE: "false",
        SOLAROPS_TRUSTED_ORIGINS: "http://127.0.0.1:3001",
        SOLAROPS_MAILBOX_PATH: "var/phase3-e2e-mailbox.jsonl",
        SOLAROPS_EVIDENCE_DIR: "var/phase3-e2e-evidence",
      },
    },
    {
      command: "node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3001",
      url: "http://127.0.0.1:3001/login",
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        SOLAROPS_API_ORIGIN: "http://127.0.0.1:8001",
        SOLAROPS_NEXT_DIST_DIR: ".next-qa",
        NEXT_PUBLIC_SOLAROPS_ENV: "development",
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  ],
});
