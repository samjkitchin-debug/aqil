import { expect, test } from "@playwright/test";

test.describe("research insight UI", () => {
  test.beforeEach(async ({ context, baseURL }) => {
    await context.addCookies([
      {
        name: "aqil_founder_insight",
        value: "ci-founder-test-token",
        url: baseURL!,
      },
    ]);
  });

  test("shows fixture research on Today and Research", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("research-insight")).toBeVisible();
    await expect(page.getByTestId("research-preview-banner")).toContainText(
      /demonstration|internal research preview/i,
    );

    await page.goto("/research");
    await expect(page.getByTestId("research-insight")).toBeVisible();
    await expect(page.getByTestId("research-unemployment-chart")).toBeVisible();
    await expect(page.getByTestId("research-run-ref")).toContainText("m3-e2e-run");
  });

  test("hides founder research without authorisation cookie", async ({
    browser,
  }) => {
    test.skip(
      process.env.E2E_USE_DEV_SERVER === "true",
      "Dev server allows local founder preview without a cookie",
    );
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto("/research");
    await expect(page.getByTestId("research-empty-state")).toBeVisible();
    await expect(page.getByTestId("research-insight")).toHaveCount(0);
    await context.close();
  });

  test("does not expose database credentials in HTML", async ({ page }) => {
    await page.goto("/research");
    const html = await page.content();
    expect(html).not.toMatch(/research_worker/);
    expect(html).not.toMatch(/postgresql:\/\//);
  });
});
