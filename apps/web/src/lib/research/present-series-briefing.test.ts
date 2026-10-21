import assert from "node:assert/strict";
import test from "node:test";

import { presentSeriesBriefing, unpublishedMonths, type LiveSeriesRetrieval } from "./present-series-briefing.ts";

const series: LiveSeriesRetrieval = {
  sourceId: "bls_cps_unemployment_rate",
  datasetId: "bls.ln.LNS14000000",
  retrievedAt: "2026-10-21T07:31:45.000Z",
  seriesProvenance: "latest_revised",
  unit: "percent",
  seasonalAdjustment: "seasonally_adjusted",
  frequency: "monthly",
  periods: ["2025-09-01", "2025-11-01", "2025-12-01"],
  latestPeriod: "2025-12-01",
  latestRawValue: "4.1",
};

test("a missing month inside the span is named and not filled", () => {
  assert.deepEqual(unpublishedMonths(series.periods), ["2025-10"]);
  const copy = presentSeriesBriefing(series);
  assert.match(
    copy.sourceLine,
    /^Source bls_cps_unemployment_rate\. Dataset bls\.ln\.LNS14000000\. Latest revised, seasonally adjusted, percent\.$/,
  );
  assert.match(copy.notice, /not a news announcement/i);
  assert.match(copy.gapLine ?? "", /Permanently missing: October 2025/);
  assert.match(copy.gapLine ?? "", /did not publish this month/);
  assert.match(copy.gapLine ?? "", /Nothing was filled in/);
  assert.match(copy.latestLine, /December 2025, 4.1 percent/);
  assert.doesNotMatch(copy.notice, /conclusion is/);
});

test("a continuous span has no gap line", () => {
  const copy = presentSeriesBriefing({
    ...series,
    periods: ["2025-09-01", "2025-10-01"],
    latestPeriod: "2025-10-01",
  });
  assert.equal(copy.gapLine, null);
  assert.match(copy.spanLine, /2 monthly observations/);
});
