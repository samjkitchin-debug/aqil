import { expect, test } from "@playwright/test";

test.describe("research insight UI", () => {
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

  test("does not expose database credentials in HTML", async ({ page }) => {
    await page.goto("/research");
    const html = await page.content();
    expect(html).not.toMatch(/research_worker/);
    expect(html).not.toMatch(/postgresql:\/\//);
  });
});
