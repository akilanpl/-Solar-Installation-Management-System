import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

// Full-stack layout regression: uses the supported development seed and real
// login/session APIs, with no mocked responses or browser-side account state.
for (const width of [390, 768, 1280]) {
  test(`authenticated workspace navigation is usable at ${width}px`, async ({ page }) => {
    const accounts = JSON.parse(readFileSync(resolve(process.cwd(), "../../var/demo-credentials.json"), "utf8"));
    const account = accounts["customer.demo@solarops.example.com"];
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/login");
    await page.waitForFunction(() => document.body.dataset.loginReady === "1");
    await page.locator('input[name="identifier"]').fill(account.identifier);
    await page.getByLabel("Password", { exact: true }).fill(account.password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/customer$/);
    const dock = page.getByRole("complementary", { name: "Workspace", exact: true });
    await expect(dock).toBeVisible();
    const bounds = await dock.boundingBox();
    expect(bounds).not.toBeNull();
    if (width <= 768) {
      expect(bounds!.y).toBeGreaterThan(700);
      expect(bounds!.x).toBeGreaterThanOrEqual(0);
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
      for (const link of await dock.getByRole("link").all()) {
        await link.focus();
        const size = await link.boundingBox();
        expect(size!.width).toBeGreaterThanOrEqual(44);
        expect(size!.height).toBeGreaterThanOrEqual(44);
      }
      const signOut = dock.getByRole("button", { name: "Sign out" });
      await signOut.focus();
      const button = await signOut.boundingBox();
      expect(button!.x + button!.width).toBeLessThanOrEqual(width);
    } else {
      expect(bounds!.x).toBe(0);
      expect(bounds!.height).toBeGreaterThan(bounds!.width);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  });
}
