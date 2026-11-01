import { defineConfig, devices } from "@playwright/test";

const database = process.env.SOLAROPS_E2E_DATABASE_URL;
if (!database) throw new Error("Use apps/api/scripts/run_ci_browser.py for isolated QA.");
const target = new URL(database);
if (target.pathname !== "/solarops_test" || !["localhost", "127.0.0.1"].includes(target.hostname)) {
  throw new Error("Main browser QA requires local solarops_test.");
}

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  workers: 1,
  outputDir: process.env.SOLAROPS_E2E_OUTPUT_DIR ?? "./test-results/main-qa",
  use: {
    baseURL: "http://127.0.0.1:3011",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `cd ../api && ${process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python"} -m uvicorn app.main:app --host 127.0.0.1 --port 8011`,
      url: "http://127.0.0.1:8011/api/v1/ready",
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        SOLAROPS_DATABASE_URL: database, SOLAROPS_APP_ENV: "development",
        SOLAROPS_COOKIE_SECURE: "false", SOLAROPS_SMTP_HOST: "",
        SOLAROPS_TRUSTED_ORIGINS: "http://127.0.0.1:3011",
      },
    },
    {
      command: "node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3011",
      url: "http://127.0.0.1:3011/login",
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        SOLAROPS_API_ORIGIN: "http://127.0.0.1:8011",
        NEXT_PUBLIC_SOLAROPS_ENV: "development", NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
