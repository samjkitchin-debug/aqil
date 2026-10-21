import assert from "node:assert/strict";
import test from "node:test";

import {
  directionPhrase,
  quarterStartingLabel,
  sloosLimitationCopy,
  sloosMonitorCopy,
  whyItMatters,
} from "./present-sloos-reading.ts";

test("a positive SLOOS direction stays a survey description", () => {
  assert.equal(directionPhrase("net_tightening"), "net tightening");
  assert.equal(quarterStartingLabel("2026-07-01"), "1 July 2026");
  assert.match(sloosMonitorCopy(), /next Senior Loan Officer Opinion Survey/);
  assert.match(sloosLimitationCopy(["Survey-based."]), /not a point-in-time reconstruction/);
  assert.match(whyItMatters("balanced_net_tightening_and_easing", "Not a predictor."), /zero share/);
  assert.match(whyItMatters("balanced_net_tightening_and_easing", "Not a predictor."), /Not a predictor/);
});
