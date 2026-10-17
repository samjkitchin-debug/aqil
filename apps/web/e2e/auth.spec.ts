import { expect, test } from "@playwright/test";

const privateRoutes = ["/", "/explore", "/calendar", "/learn", "/research", "/my-wealth"];

test.describe("authentication gate", () => {
  for (const route of privateRoutes) {
    test(`anonymous ${route} does not render private payloads`, async ({ page }) => {
      const response = await page.goto(route);
      expect(response?.status()).toBeLessThan(400);
      await expect(page).toHaveURL(/\/login/);
      const html = await page.content();
      expect(html).not.toMatch(/eyJ[A-Za-z0-9_-]{20,}/);
      expect(html).not.toContain("m3-e2e-run");
    });
  }

  test("rejects an open redirect on the login next parameter", async ({ page }) => {
    await page.goto("/login?next=https://evil.example/phish");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    const next = page.locator('input[name="next"]');
    await expect(next).toHaveValue("/");
  });

  test("auth callback without a code returns to login", async ({ page }) => {
    await page.goto("/auth/callback?error=access_denied");
    await expect(page).toHaveURL(/\/login\?error=provider_denied/);
    await expect(page.getByTestId("login-error")).toBeVisible();
  });

  test("my wealth does not claim a synthetic portfolio while signed out", async ({ page }) => {
    await page.goto("/my-wealth");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByTestId("wealth-empty")).toHaveCount(0);
    const html = await page.content();
    expect(html.toLowerCase()).not.toContain("semiconductor");
  });
});
