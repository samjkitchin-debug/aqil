import assert from "node:assert/strict";
import test from "node:test";

import {
  intelligenceHome,
  intelligenceNav,
  isIntelligencePath,
  isPrimaryActive,
  primaryNav,
} from "./navigation.ts";

test("Intelligence opens conditions and keeps Upcoming on the calendar", () => {
  assert.deepEqual(
    primaryNav.map((item) => item.label),
    ["Today", "My Wealth", "Intelligence"],
  );
  assert.equal(primaryNav.find((item) => item.label === "Intelligence")?.href, "/conditions");
  assert.equal(intelligenceHome, "/conditions");
  assert.equal(intelligenceNav[0]?.href, "/conditions");
  assert.equal(intelligenceNav.find((item) => item.label === "Upcoming")?.href, "/calendar");
  assert.equal(intelligenceNav.find((item) => item.label === "Evidence")?.href, "/research");
  assert.equal(intelligenceNav.find((item) => item.label === "Exposures")?.href, "/explore");
  assert.equal(isIntelligencePath("/conditions"), true);
  assert.equal(isIntelligencePath("/calendar"), true);
  assert.equal(isIntelligencePath("/research"), true);
  assert.equal(isIntelligencePath("/my-wealth"), false);
  assert.equal(isPrimaryActive("/calendar", "/conditions"), true);
  assert.equal(isPrimaryActive("/research", "/conditions"), true);
  assert.equal(isPrimaryActive("/conditions", "/conditions"), true);
  assert.equal(isPrimaryActive("/my-wealth", "/conditions"), false);
  assert.equal(isPrimaryActive("/", "/conditions"), false);
  assert.equal(isPrimaryActive("/conditions", "/"), false);
});
