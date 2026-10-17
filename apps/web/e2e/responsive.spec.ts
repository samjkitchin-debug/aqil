import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const publicRoutes = ["/login", "/privacy", "/tos"];
const privateRoutes = ["/", "/explore", "/calendar", "/learn", "/research", "/my-wealth"];

async function expectNoHorizontalOverflow(page: Page) {
  const metrics = await page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    const viewportWidth = window.innerWidth;
    const offenders: string[] = [];

    for (const element of document.querySelectorAll("body *")) {
      if (!(element instanceof HTMLElement)) continue;
      const style = window.getComputedStyle(element);
      if (style.display === "none" || style.visibility === "hidden") continue;
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;
      if (rect.right > viewportWidth + 1) {
        offenders.push(
          `${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ""} right=${Math.round(rect.right)}`,
        );
      }
    }

    return {
      docOverflow: root.scrollWidth > root.clientWidth + 1,
      bodyOverflow: body.scrollWidth > body.clientWidth + 1,
      offenders: offenders.slice(0, 5),
    };
  });
  expect(metrics.docOverflow, "documentElement should not scroll horizontally").toBe(
    false,
  );
  expect(metrics.bodyOverflow, "body should not scroll horizontally").toBe(false);
  expect(
    metrics.offenders,
    "no visible element should extend past the viewport (overflow-x clip is not used)",
  ).toEqual([]);
}

test.describe("responsive shell", () => {
  for (const route of publicRoutes) {
    test(`renders ${route} without horizontal overflow`, async ({ page }) => {
      await page.goto(route);
      await expect(page.getByRole("main")).toBeVisible();
      await expectNoHorizontalOverflow(page);
    });
  }

  for (const route of privateRoutes) {
    test(`requires sign-in for ${route}`, async ({ page }) => {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
      await expect(page.getByRole("button", { name: "Continue with Google" })).toBeVisible();
      await expect(page.getByTestId("research-insight")).toHaveCount(0);
      await expectNoHorizontalOverflow(page);
    });
  }

  test("primary navigation is visible and links are usable", async ({ page }) => {
    await page.goto("/");
    const nav = page.getByRole("navigation", { name: "Primary" });
    await expect(nav).toBeVisible();

    for (const label of [
      "Today",
      "Explore",
      "Calendar",
      "My wealth",
      "Learn",
      "Research",
    ]) {
      const link = nav.getByRole("link", { name: label });
      await expect(link).toBeVisible();
      await expect(link).toBeEnabled();
    }

    await nav.getByRole("link", { name: "Explore" }).click();
    await expect(page).toHaveURL(/\/login\?/);
    await expect(page.getByRole("heading", { level: 1, name: "Sign in" })).toBeVisible();
  });

  test("keyboard user can reach skip link and main content", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Skip to main content" });
    await expect(skip).toBeFocused();

    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();
  });

  test("axe smoke scan on home (automated check only)", async ({ page }) => {
    await page.goto("/");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});
