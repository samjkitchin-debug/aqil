import { expect, test } from "@playwright/test";

test.describe("research insight UI", () => {
  test("does not show founder research to an anonymous visitor", async ({ page }) => {
    await page.goto("/research");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByTestId("research-insight")).toHaveCount(0);
    await expect(page.getByTestId("research-unemployment-chart")).toHaveCount(0);
  });

  test("founder cookie does not unlock research", async ({ context, baseURL, page }) => {
    await context.addCookies([
      {
        name: "aqil_founder_insight",
        value: "ci-founder-test-token",
        url: baseURL!,
        httpOnly: true,
        sameSite: "Lax",
      },
    ]);
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByTestId("research-insight")).toHaveCount(0);
  });

  test("does not expose database credentials in the login HTML", async ({ page }) => {
    await page.goto("/login");
    const html = await page.content();
    expect(html).not.toMatch(/research_worker/);
    expect(html).not.toMatch(/postgresql:\/\//);
    expect(html).not.toMatch(/SUPABASE_SERVICE_ROLE_KEY/);
    expect(html).not.toMatch(/service_role/);
  });
});
