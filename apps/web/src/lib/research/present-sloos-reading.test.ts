import assert from "node:assert/strict";
import test from "node:test";

import {
  calculatedDifferenceCopy,
  describeStoredSloosSeries,
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
  assert.equal(
    calculatedDifferenceCopy("0.0", "8.1"),
    "Calculated difference: The later stored share is 8.1 percentage points lower than the earlier stored share. This arithmetic comparison is separate from the method calculation. It is not a forecast.",
  );
  const context = describeStoredSloosSeries([
    { period: "2026-04-01", sharePercent: "8.1" },
    { period: "2026-07-01", sharePercent: "0.0" },
    { period: "2026-01-01", sharePercent: "-1.0" },
  ]);
  assert.match(
    context?.history ?? "",
    /1 quarter is net tightening, 1 quarter is net easing, and 1 quarter is a zero net balance/,
  );
  assert.match(context?.position ?? "", /at or below 2 of 3/);
  assert.match(context?.contradiction ?? "", /later quarter above zero/);
  assert.match(context?.position ?? "", /not a probability/);
});
