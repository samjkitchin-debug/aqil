import { defineConfig } from "@playwright/test";

const port = process.env.PORT ?? "3000";
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ??
  (process.env.CI ? `http://localhost:${port}` : `http://127.0.0.1:${port}`);

const viewportProjects = [
  { name: "phone-small", width: 320, height: 568 },
  { name: "phone-large", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "laptop", width: 1280, height: 800 },
  { name: "desktop-wide", width: 1920, height: 1080 },
] as const;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: !process.env.CI,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    browserName: "chromium",
    trace: "on-first-retry",
  },
  projects: viewportProjects.map((viewport) => ({
    name: viewport.name,
    use: {
      viewport: { width: viewport.width, height: viewport.height },
    },
  })),
  webServer: {
    command: "npm run start",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      RESEARCH_INSIGHT_PATH: "fixtures/research-insight.v1.json",
      FORWARD_HORIZON_PATH: "fixtures/forward-horizon.v1.json",
      AQIL_ALLOW_RESEARCH_FIXTURE: "true",
      E2E_USE_DEV_SERVER: process.env.CI ? "true" : "false",
    },
  },
});
