import { defineConfig, devices } from "@playwright/test";
export default defineConfig({testDir:"./e2e",timeout:90000,use:{baseURL:process.env.SOLAROPS_WEB_URL??"http://127.0.0.1:3061",trace:"retain-on-failure"},projects:[{name:"chromium",use:{...devices["Desktop Chrome"]}}],workers:1});
