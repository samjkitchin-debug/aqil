import assert from "node:assert/strict";
import test from "node:test";

import {
  DEV_STORY_PATH,
  researchStoryHrefFromToday,
  shouldShowReturnToToday,
} from "./today-story-tangent-path.ts";

test("development story route is explicit", () => {
  assert.equal(researchStoryHrefFromToday(), DEV_STORY_PATH);
  assert.equal(researchStoryHrefFromToday(), "/dev/story");
});

test("return link is not used on the evidence route", () => {
  assert.equal(shouldShowReturnToToday({ from: "today" }), false);
});
