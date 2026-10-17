import { expect, test } from "@playwright/test";

test.describe("forward horizon UI", () => {
  test.beforeEach(async ({ context, baseURL }) => {
    const origin = new URL(baseURL!);
    await context.addCookies([
      {
        name: "aqil_founder_insight",
        value: "ci-founder-test-token",
        url: baseURL!,
        path: "/",
        domain: origin.hostname,
        httpOnly: true,
        sameSite: "Lax",
      },
    ]);
  });

  test("shows horizon on Today and calendar", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("forward-horizon")).toBeVisible({ timeout: 20_000 });

    await page.goto("/calendar");
    await expect(page.getByTestId("forward-calendar")).toBeVisible();

    await page.goto("/");
    await expect(page.getByText("Schedule: official (confirmed)").first()).toBeVisible();
    await expect(page.getByText("Materiality not assessed").first()).toBeVisible();
    await expect(page.getByText("Schedule: demonstration data").first()).toBeVisible();
  });

  test("shows ETF explore and forward research detail", async ({ page }) => {
    await page.goto("/explore");
    await expect(page.getByTestId("forward-etf-explore")).toBeVisible();
    await expect(page.getByText("Verified instrument identity")).toBeVisible();
    await expect(page.getByText(/synthetic demonstration data/i)).toBeVisible();

    await page.goto("/research");
    await expect(page.getByTestId("forward-research-detail")).toBeVisible();
    await expect(page.getByText("Synthetic demonstration scenario")).toBeVisible();
    await expect(page.getByText("Loaded from the frozen record")).toBeVisible();
    await expect(page.getByTestId("forward-outcome-block")).toBeVisible();
    await expect(page.getByText("Synthetic demonstration outcome")).toBeVisible();
  });
});
