import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e/phase4c",
  timeout: 120_000,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "../../var/phase4c/evidence/browser-results.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:3143",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command:
        "cd ../api && SOLAROPS_APP_ENV=test SOLAROPS_DATABASE_URL=postgresql+psycopg://akilan@127.0.0.1:5432/solarops_4c_preview SOLAROPS_SECRET_KEY=phase4c-preview-local-secret-not-production SOLAROPS_TRUSTED_ORIGINS=http://127.0.0.1:3143 SOLAROPS_LOGIN_IP_LIMIT=1000 SOLAROPS_LOGIN_IDENTIFIER_LIMIT=1000 .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8143",
      url: "http://127.0.0.1:8143/api/v1/health",
      reuseExistingServer: false,
    },
    {
      command:
        "SOLAROPS_API_ORIGIN=http://127.0.0.1:8143 npx next start --hostname 127.0.0.1 --port 3143",
      url: "http://127.0.0.1:3143/login",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
