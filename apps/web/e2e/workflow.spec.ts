import { expect, test, type Browser, type Page } from "@playwright/test";

const JPEG = Buffer.from([0xff, 0xd8, 0xff, 0x00, 0x73, 0x6f, 0x6c, 0x61, 0x72]);

async function staff(browser: Browser, portal: string, employeeId: string): Promise<Page> {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("I am signing in as").selectOption(portal);
  await page.getByLabel("Employee ID").fill(employeeId);
  const password = process.env.SOLAROPS_SEED_PASSWORD;
  if (!password) throw new Error("Set SOLAROPS_SEED_PASSWORD to the seeded staff password.");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  return page;
}

test("enquiry reaches a confirmed order through the live workspaces", async ({ page, browser }) => {
  test.setTimeout(180_000);
  const email = `meera.${Date.now()}@example.com`;
  await page.goto("/signup");
  await page.getByLabel("Full name").fill("Meera Shah");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mobile").fill("9845011122");
  await page.getByLabel("Password").fill("Solarops123");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("button", { name: "Load code from local mailbox" }).click();
  await page.getByRole("button", { name: "Verify email" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("Solarops123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "New enquiry" }).first().click();
  await page.getByLabel("Estimated monthly electricity bill (₹)").fill("4500");
  await page.getByLabel("Site address").fill("8 Hill Road");
  await page.getByLabel("City").fill("Hyderabad");
  await page.getByLabel("State").fill("Telangana");
  await page.getByLabel("PIN code").fill("500032");
  await page.getByRole("button", { name: "Submit enquiry" }).click();
  const reference = (await page.getByRole("heading", { level: 1 }).textContent()) ?? "";
  expect(reference).toMatch(/ENQ-/);

  await page.goto("/sales");
  await expect(page.getByRole("heading", { name: "Access denied" })).toBeVisible();

  const sales = await staff(browser, "sales", "EMP-SALES-001");
  await expect(sales.getByRole("heading", { name: "Enquiries" })).toBeVisible();
  await sales.getByRole("link", { name: reference }).click();
  await sales.getByRole("button", { name: "Update status" }).click();
  await sales.getByRole("button", { name: "Save status" }).click();
  await expect(sales.getByText("Under review").first()).toBeVisible();
  await sales.getByLabel("Next status").selectOption("qualified");
  await sales.getByLabel("Shadow-free area (m²)").fill("40");
  await sales.getByRole("button", { name: "Update status" }).click();
  await sales.getByRole("button", { name: "Save status" }).click();
  await expect(sales.getByText("Qualified").first()).toBeVisible();
  await sales.getByRole("button", { name: "Open survey" }).click();
  await expect(sales.getByRole("heading", { name: /SUR-/ })).toBeVisible();
  await sales.getByLabel("Technician").selectOption({ label: "Kavya Rao (EMP-TECH-001)" });
  await sales.getByRole("button", { name: "Assign technician" }).click();
  await expect(sales.getByText("Assigned").first()).toBeVisible();

  const technician = await staff(browser, "technician", "EMP-TECH-001");
  await expect(technician.getByRole("heading", { name: "Assigned surveys" })).toBeVisible();
  await technician.getByRole("link", { name: /SUR-/ }).click();
  await technician.getByRole("button", { name: "Start survey" }).click();
  await technician.getByLabel("Tilt (degrees)").fill("95");
  await technician.getByRole("button", { name: "Submit survey" }).click();
  await expect(technician.getByText("Enter a value from 0 to 90.")).toBeVisible();
  await technician.getByLabel("Azimuth (degrees)").fill("180");
  await technician.getByLabel("Tilt (degrees)").fill("18");
  await technician.getByLabel("Shadow-free area (m²)").fill("36.5");
  await technician.getByLabel("Cable distance (m)").fill("22");
  await technician.getByLabel("Notes").fill("South-facing concrete roof with clear afternoon sun.");
  await technician.getByLabel("Survey evidence").setInputFiles({
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("not an image"),
  });
  await expect(technician.getByText(/JPEG|PNG|WebP|PDF|not accepted|evidence/i)).toBeVisible();
  await technician.getByLabel("Survey evidence").setInputFiles({
    name: "roof.jpg",
    mimeType: "image/jpeg",
    buffer: JPEG,
  });
  await expect(technician.getByText("roof.jpg")).toBeVisible();
  await technician.getByRole("button", { name: "Submit survey" }).click();
  await technician.getByRole("button", { name: "Submit" }).click();
  await expect(technician.getByText("Submitted").first()).toBeVisible();

  const repeated = await technician.evaluate(async () => {
    const token = decodeURIComponent(document.cookie.split("; ").find((part) => part.startsWith("solarops_csrf="))?.split("=")[1] ?? "");
    const surveyId = window.location.pathname.split("/").pop();
    const response = await fetch(`/api/v1/surveys/${surveyId}/submission`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
      body: JSON.stringify({
        azimuth_deg: "180",
        tilt_deg: "18",
        shadow_free_area_sqm: "36.5",
        cable_distance_m: "22",
        grid_connection: "suitable",
        notes: "Repeated submission should be rejected.",
      }),
    });
    return response.status;
  });
  expect(repeated).toBe(409);

  await sales.reload();
  await sales.getByLabel("Review note").fill("Measurements match the qualified roof.");
  await sales.getByRole("button", { name: "Approve survey" }).click();
  await sales.getByRole("button", { name: "Approve" }).click();
  await expect(sales.getByText("Approved").first()).toBeVisible();
  await sales.getByRole("button", { name: "Issue quotation" }).click();
  await sales.getByRole("button", { name: "Issue quotation" }).last().click();
  await expect(sales.getByRole("heading", { name: /QTN-/ })).toBeVisible();
  const quoteHeading = (await sales.getByRole("heading", { level: 1 }).textContent()) ?? "";

  await page.goto("/customer/quotations");
  await page.getByRole("link", { name: /QTN-/ }).click();
  await expect(page.getByText(quoteHeading.split("·")[0].trim()).first()).toBeVisible();
  await page.getByRole("button", { name: /Accept version/ }).click();
  await page.getByRole("button", { name: "Accept quotation" }).click();
  await expect(page.getByText("Accepted").first()).toBeVisible();
  await page.getByRole("button", { name: "Start test payment" }).click();
  await page.getByRole("button", { name: "Start test payment" }).last().click();
  await expect(page.getByText("TEST ONLY").first()).toBeVisible();
  await page.getByRole("button", { name: "Leave unresolved" }).click();
  await expect(page.getByText("Unresolved").first()).toBeVisible();
  await expect(page.getByText("This payment is not verified.")).toBeVisible();
  await page.getByRole("button", { name: "Start test payment" }).click();
  await page.getByRole("button", { name: "Start test payment" }).last().click();
  await page.getByRole("button", { name: "Record test success" }).click();
  await expect(page.getByText("Verified").first()).toBeVisible();

  await sales.getByRole("button", { name: "Confirm order" }).click();
  await sales.getByRole("button", { name: "Confirm order" }).last().click();
  await expect(sales.getByRole("heading", { name: /ORD-/ })).toBeVisible();
  const orderReference = (await sales.getByRole("heading", { level: 1 }).textContent()) ?? "";
  const duplicate = await sales.evaluate(async () => {
    const token = decodeURIComponent(document.cookie.split("; ").find((part) => part.startsWith("solarops_csrf="))?.split("=")[1] ?? "");
    const quoteLink = document.querySelector("a[href*='/sales/quotations/']");
    const quotationId = quoteLink?.getAttribute("href")?.split("/").pop();
    const response = await fetch("/api/v1/orders", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": token,
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({ quotation_id: quotationId }),
    });
    return response.status;
  });
  expect(duplicate).toBe(409);

  await sales.getByRole("link", { name: "Installation scheduling" }).click();
  await expect(sales.getByText("Unscheduled. This request has no installation slot.")).toBeVisible();

  const warehouse = await staff(browser, "warehouse", "EMP-WH-001");
  await expect(warehouse.getByRole("heading", { name: "Preparation queue" })).toBeVisible();
  await expect(warehouse.getByText(orderReference)).toBeVisible();
  await expect(warehouse.getByText(/Stock is not deducted/)).toBeVisible();

  await page.goto("/customer/orders");
  await expect(page.getByRole("link", { name: orderReference })).toBeVisible();
});

test("a failed API response is shown instead of invented data", async ({ page }) => {
  await page.route("**/api/v1/enquiries**", async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "unavailable", message: "The enquiry list could not be loaded." } }),
    });
  });
  const email = `nisha.${Date.now()}@example.com`;
  await page.goto("/signup");
  await page.getByLabel("Full name").fill("Nisha Rao");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mobile").fill("9845011133");
  await page.getByLabel("Password").fill("Solarops123");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("button", { name: "Load code from local mailbox" }).click();
  await page.getByRole("button", { name: "Verify email" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("Solarops123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("The enquiry list could not be loaded.")).toBeVisible();
});
