import { defineConfig, devices } from "@playwright/test";

// Phase 4B isolated acceptance: disposable preview DB (solarops_4b_preview)
// served by the API on 8012 and Next.js on 3012. Playwright owns both
// servers for the run; nothing touches the 8000/3000 integration ports.
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["warranty-4b.spec.ts"],
  timeout: 120_000,
  use: {
    baseURL: "http://127.0.0.1:3012",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "cd ../api && SOLAROPS_LOGIN_IP_LIMIT=100 SOLAROPS_LOGIN_IDENTIFIER_LIMIT=100 uv run uvicorn app.main:app --host 127.0.0.1 --port 8012",
      url: "http://127.0.0.1:8012/api/v1/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "SOLAROPS_API_ORIGIN=http://127.0.0.1:8012 npx next dev --hostname 127.0.0.1 --port 3012",
      url: "http://127.0.0.1:3012/login",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
