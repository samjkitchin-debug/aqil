import assert from "node:assert/strict";
import test from "node:test";

import {
  LIVE_PUBLICATION_FILTER,
  OPERATIONAL_CALENDAR_FILTER,
} from "./operational-sources.ts";

test("live publications exclude fixture retrievals", () => {
  assert.match(LIVE_PUBLICATION_FILTER, /collection_mode = 'live'/);
  assert.equal(LIVE_PUBLICATION_FILTER.includes("fixture"), false);
});

test("upcoming catalysts stay on the official BLS calendar", () => {
  assert.match(OPERATIONAL_CALENDAR_FILTER, /bls_ics_schedule/);
  assert.match(OPERATIONAL_CALENDAR_FILTER, /event:fixture:%/);
  assert.match(OPERATIONAL_CALENDAR_FILTER, /www\.bls\.gov/);
});
