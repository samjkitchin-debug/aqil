import { expect, test } from "@playwright/test";

test.describe("forward horizon UI", () => {
  test.beforeEach(async ({ context, baseURL }) => {
    await context.addCookies([
      {
        name: "aqil_founder_insight",
        value: "ci-founder-test-token",
        url: baseURL!,
        httpOnly: true,
        sameSite: "Lax",
      },
    ]);
  });

  test("shows horizon on Today and calendar", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("forward-horizon")).toBeVisible();

    await page.goto("/calendar");
    await expect(page.getByTestId("forward-horizon")).toBeVisible();
  });

  test("shows ETF explore and forward research detail", async ({ page }) => {
    await page.goto("/explore");
    await expect(page.getByTestId("forward-etf-explore")).toBeVisible();

    await page.goto("/research");
    await expect(page.getByTestId("forward-research-detail")).toBeVisible();
    await expect(page.getByTestId("forward-outcome-block")).toBeVisible();
  });
});
