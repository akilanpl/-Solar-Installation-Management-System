import { resolve } from "node:path";
import { defineConfig, devices } from "@playwright/test";

const database = process.env.SOLAROPS_DATABASE_URL;
if (!database) throw new Error("Missing isolated browser database");
const target = new URL(database);
if (!['127.0.0.1', 'localhost'].includes(target.hostname) ||
    !/^solarops_browser_ci(?:_[a-f0-9]{12})?$/.test(target.pathname.slice(1)) ||
    target.pathname.slice(1) !== process.env.SOLAROPS_BROWSER_DATABASE_NAME ||
    process.env.SOLAROPS_APP_ENV !== 'development' || !process.env.SOLAROPS_SEED_PASSWORD) {
  throw new Error("Refusing an unisolated browser target");
}
// An owner-pinned bootstrap controller can run its assertions against a separate
// unchanged application checkout. The baseline preflight validates both SHAs.
const applicationRoot = resolve(process.env.SOLAROPS_ACCEPTANCE_APPLICATION_ROOT ?? '../..');
const evidenceRoot = resolve('../../var/browser-ci');
const quote = (value: string) => "'" + value.replaceAll("'", "'\\''") + "'";
export default defineConfig({
  testDir: './e2e/ci', fullyParallel: false, workers: 1, retries: 0,
  forbidOnly: true, timeout: 360_000, expect: { timeout: 15_000 },
  outputDir: '../../var/browser-ci/test-results',
  reporter: [['list'], ['html', { outputFolder: '../../var/browser-ci/report', open: 'never' }],
    ['junit', { outputFile: '../../var/browser-ci/junit.xml' }],
    ['json', { outputFile: '../../var/browser-ci/results.json' }]],
  use: { baseURL: 'http://127.0.0.1:3001', timezoneId: 'UTC', actionTimeout: 30_000, navigationTimeout: 30_000,
    trace: 'on', screenshot: 'only-on-failure', video: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    { cwd: resolve(applicationRoot, 'apps/api'), command: `uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 > ${quote(resolve(evidenceRoot, 'api.log'))} 2>&1`,
      url: 'http://127.0.0.1:8001/api/v1/ready', reuseExistingServer: false, timeout: 60_000 },
    { cwd: resolve(applicationRoot, 'apps/web'), command: `node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3001 > ${quote(resolve(evidenceRoot, 'web.log'))} 2>&1`,
      url: 'http://127.0.0.1:3001/login', reuseExistingServer: false, timeout: 60_000 },
  ],
});
