import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir:"./e2e/release",timeout:120000,workers:1,
  use:{baseURL:process.env.SOLAROPS_WEB_URL??"http://127.0.0.1:3061",trace:"retain-on-failure",screenshot:"only-on-failure"},
  projects:[{name:"chromium",use:{...devices["Desktop Chrome"]}},{name:"firefox",testMatch:"accessibility.spec.ts",use:{...devices["Desktop Firefox"]}},{name:"webkit",testMatch:"accessibility.spec.ts",use:{...devices["Desktop Safari"]}}],
});
