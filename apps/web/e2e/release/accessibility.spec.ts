import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { discoverPages, owner } from "./routes";

function account(role: string) {
  const root = resolve(process.cwd(), "../..");
  const demos = JSON.parse(readFileSync(resolve(root, "var/demo-credentials.json"), "utf8"));
  if (role === "customer") return demos["customer.demo@solarops.example.com"];
  const codes: Record<string, string> = {sales:"EMP-SALES-001",technician:"EMP-TECH-001",support:"EMP-SUP-001",admin:"EMP-ADMIN-001",warehouse_staff:"EMP-WH-001"};
  return {identifier:codes[role],password:readFileSync(resolve(root,"var/dev-seed-password.txt"),"utf8").trim()};
}
async function login(page: Page, role: string) {
  const user = account(role);
  await page.goto("/login");
  await page.waitForFunction(() => document.body.dataset.loginReady === "1");
  if (role !== "customer") await page.getByLabel("I am signing in as").selectOption(role === "warehouse_staff" ? "warehouse" : role);
  await page.locator('input[name="identifier"]').fill(user.identifier);
  await page.getByLabel("Password",{exact:true}).fill(user.password);
  await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page).not.toHaveURL(/\/login/);
}
function concrete(route: string) {
  if (!route.includes("[")) return route;
  const path = resolve(process.cwd(),"../../var/browser-fixtures.json");
  if (!existsSync(path)) throw new Error(`Missing populated fixture for ${route}; generate through supported business workflow and record in ignored var/browser-fixtures.json`);
  const value = JSON.parse(readFileSync(path,"utf8"))[route];
  if (typeof value !== "string" || value.includes("[") || !value.startsWith("/")) throw new Error(`No concrete saved-record route for ${route}`);
  return value;
}
for (const route of discoverPages()) {
  for (const width of [390,768,1280]) {
    test(`saved page ${route} accessible at ${width}`,async({page})=>{
      const role=owner(route); const failures:string[]=[];
      page.on("pageerror",error=>failures.push(error.message));
      await page.setViewportSize({width,height:844});
      if(role!=="public") await login(page,role);
      const response=await page.goto(concrete(route));
      expect(response?.status()).toBe(200);
      await expect(page.locator("main")).toBeVisible();
      await expect(page.getByRole("status").filter({hasText:/Loading/i})).toHaveCount(0,{timeout:15000});
      await expect(page.getByText("Application error",{exact:false})).toHaveCount(0);
      if(route.includes("[")) await expect(page.getByText(/not found/i)).toHaveCount(0);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      const axe=await new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
      expect(axe.violations.filter(v=>v.impact==="serious"||v.impact==="critical")).toEqual([]);
      await page.keyboard.press("Tab");
      expect(await page.evaluate(()=>document.activeElement?.tagName)).not.toBe("BODY");
      await page.reload();
      await expect(page.locator("main")).toBeVisible();
      expect(failures).toEqual([]);
    });
  }
  if(owner(route)!=="public"&&owner(route)!=="customer"&&route!=="/security") {
    test(`customer denied ${route}`,async({page})=>{
      await login(page,"customer");
      await page.goto(route.replace(/\[[^\]]+\]/g,"00000000-0000-4000-8000-000000000001"));
      await expect(page.getByText(/access denied|not available for your role|not authorized|do not have access/i)).toBeVisible();
    });
  }
}
