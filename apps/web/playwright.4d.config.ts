import { defineConfig, devices } from "@playwright/test";

// Phase 4D isolated acceptance: disposable preview DB (solarops_4d_preview)
// served by the API on 8014 and Next.js on 3014. Nothing touches the
// 8000/3000 integration ports or any teammate database.
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["intelligence-4d.spec.ts"],
  timeout: 120_000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3014",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "cd ../api && SOLAROPS_APP_ENV=development SOLAROPS_DATABASE_URL=postgresql+psycopg://solarops:solarops@127.0.0.1:5432/solarops_4d_preview SOLAROPS_SECRET_KEY=test-secret-key-not-for-production-use!! SOLAROPS_TRUSTED_ORIGINS=http://127.0.0.1:3014,http://localhost:3014 uv run uvicorn app.main:app --host 127.0.0.1 --port 8014",
      url: "http://127.0.0.1:8014/api/v1/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "SOLAROPS_API_ORIGIN=http://127.0.0.1:8014 npx next dev --hostname 127.0.0.1 --port 3014",
      url: "http://127.0.0.1:3014/login",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
