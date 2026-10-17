import { expect, test } from "@playwright/test";

test.describe("forward horizon UI", () => {
  test("does not show horizon data without an authorised session", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByTestId("forward-horizon")).toHaveCount(0);

    await page.goto("/calendar");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByText("Schedule verified")).toHaveCount(0);
  });

  test("does not show ETF explore or research detail without a session", async ({ page }) => {
    await page.goto("/explore");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByTestId("forward-etf-explore")).toHaveCount(0);

    await page.goto("/research");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByTestId("forward-research-detail")).toHaveCount(0);
    await expect(page.getByTestId("forward-outcome-block")).toHaveCount(0);
  });
});
