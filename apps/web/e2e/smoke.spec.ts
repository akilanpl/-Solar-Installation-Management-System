import { expect, test } from "@playwright/test";

test("login renders and switches between customer and staff forms", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in to SolarOps" })).toBeVisible();
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute("type", "password");
  await page.getByLabel("I am signing in as").selectOption("sales");
  await expect(page.getByRole("textbox", { name: /^Employee ID/ })).toBeVisible();
  await page.getByLabel("I am signing in as").selectOption("customer");
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Create an account" })).toHaveAttribute("href", "/signup");
  expect(errors).toEqual([]);
});
