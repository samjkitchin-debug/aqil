import assert from "node:assert/strict";
import test from "node:test";

import {
  TODAY_STORY_QUERY_KEY,
  TODAY_STORY_QUERY_VALUE,
  researchStoryHrefFromToday,
  shouldShowReturnToToday,
} from "./today-story-tangent-path.ts";

test("Today links to the synthetic story with a return marker", () => {
  const href = researchStoryHrefFromToday();
  assert.equal(href, `/research?${TODAY_STORY_QUERY_KEY}=${TODAY_STORY_QUERY_VALUE}`);
});

test("return link appears only when the story was opened from Today", () => {
  assert.equal(shouldShowReturnToToday({}), false);
  assert.equal(shouldShowReturnToToday({ from: "explore" }), false);
  assert.equal(shouldShowReturnToToday({ from: TODAY_STORY_QUERY_VALUE }), true);
  assert.equal(shouldShowReturnToToday({ from: ["today", "other"] }), true);
});
