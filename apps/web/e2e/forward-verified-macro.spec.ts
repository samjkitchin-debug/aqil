import { expect, test } from "@playwright/test";

test.describe("verified macro horizon bundle", () => {
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

  test("today and research show verified macro intelligence", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("forward-horizon")).toBeVisible();
    await expect(page.getByText("FOMC meeting — federal funds rate decision")).toBeVisible();
    await expect(page.getByText("Forward intelligence preview")).toBeVisible();

    await page.goto("/research");
    await expect(page.getByTestId("forward-research-detail")).toBeVisible();
    await expect(page.getByText("Source-backed pre-event assessment")).toBeVisible();
    await expect(page.getByText(/Expected information/)).toBeVisible();
    await expect(page.getByText(/No-action conclusion/)).toBeVisible();
    await expect(page.getByTestId("forward-outcome-block")).toHaveCount(0);
  });
});
