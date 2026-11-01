import { defineConfig, devices } from "@playwright/test";

// Phase 4E isolated acceptance: disposable preview DB (solarops_4e_preview)
// served by the API on 8015 and Next.js on 3015. Playwright owns both
// servers for the run; nothing touches the 8000/3000 integration ports or
// another agent's database. Ports 8015/3015 were verified free.
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["passkey-4e.spec.ts", "mfa-4e.spec.ts", "workflows-4e.spec.ts"],
  timeout: 180_000,
  // One worker: the specs share preview staff accounts, and parallel runs
  // race on tech4e's MFA factor state.
  workers: 1,
  use: {
    baseURL: "http://localhost:3015",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "cd ../api && SOLAROPS_APP_ENV=development SOLAROPS_LOGIN_IP_LIMIT=200 SOLAROPS_LOGIN_IDENTIFIER_LIMIT=200 SOLAROPS_OTP_ATTEMPT_LIMIT=200 SOLAROPS_DATABASE_URL=postgresql+psycopg://solarops:solarops@127.0.0.1:5432/solarops_4e_preview SOLAROPS_SECRET_KEY=preview-only-secret-key-32-chars-min!! SOLAROPS_TRUSTED_ORIGINS=http://localhost:3015 SOLAROPS_WEBAUTHN_RP_ID=localhost SOLAROPS_WEBAUTHN_ALLOWED_ORIGINS=http://localhost:3015 SOLAROPS_MAILBOX_PATH=/tmp/solarops-4e-mailbox.jsonl uv run uvicorn app.main:app --host 127.0.0.1 --port 8015",
      url: "http://127.0.0.1:8015/api/v1/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command:
        "SOLAROPS_API_ORIGIN=http://127.0.0.1:8015 NEXT_PUBLIC_SOLAROPS_PASSKEYS=on NEXT_PUBLIC_SOLAROPS_OFFLINE=on npx next dev --hostname 127.0.0.1 --port 3015",
      url: "http://localhost:3015/login",
      reuseExistingServer: true,
      timeout: 180_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
