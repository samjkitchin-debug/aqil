import assert from "node:assert/strict";
import test from "node:test";

import {
  intelligenceHome,
  intelligenceNav,
  isIntelligencePath,
  isPrimaryActive,
  primaryNav,
} from "./navigation.ts";

test("Intelligence opens the dashboard and keeps three sections", () => {
  assert.deepEqual(
    primaryNav.map((item) => item.label),
    ["Today", "My Wealth", "Intelligence"],
  );
  assert.equal(primaryNav.find((item) => item.label === "Intelligence")?.href, "/conditions");
  assert.equal(intelligenceHome, "/conditions");
  assert.deepEqual(
    intelligenceNav.map((item) => item.label),
    ["Dashboard", "Methodologies", "Insights"],
  );
  assert.equal(intelligenceNav[0]?.href, "/conditions");
  assert.equal(intelligenceNav[1]?.href, "/intelligence/methodologies");
  assert.equal(intelligenceNav[2]?.href, "/intelligence/insights");
  assert.equal(intelligenceNav.find((item) => item.label === "Upcoming"), undefined);
  assert.equal(intelligenceNav.find((item) => item.label === "Evidence"), undefined);
  assert.equal(intelligenceNav.find((item) => item.label === "Exposures"), undefined);
  assert.equal(isIntelligencePath("/conditions"), true);
  assert.equal(isIntelligencePath("/intelligence/methodologies"), true);
  assert.equal(isIntelligencePath("/intelligence/methodologies/bry-boschan-spencer15"), true);
  assert.equal(isIntelligencePath("/intelligence/insights"), true);
  assert.equal(isIntelligencePath("/calendar"), true);
  assert.equal(isIntelligencePath("/research"), true);
  assert.equal(isIntelligencePath("/explore"), false);
  assert.equal(isIntelligencePath("/my-wealth"), false);
  assert.equal(isPrimaryActive("/calendar", "/conditions"), true);
  assert.equal(isPrimaryActive("/research", "/conditions"), true);
  assert.equal(isPrimaryActive("/intelligence/insights", "/conditions"), true);
  assert.equal(isPrimaryActive("/explore", "/conditions"), false);
  assert.equal(isPrimaryActive("/conditions", "/conditions"), true);
  assert.equal(isPrimaryActive("/my-wealth", "/conditions"), false);
  assert.equal(isPrimaryActive("/", "/conditions"), false);
  assert.equal(isPrimaryActive("/conditions", "/"), false);
});
