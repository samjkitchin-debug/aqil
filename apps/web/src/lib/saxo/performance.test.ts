import assert from "node:assert/strict";
import test from "node:test";

import { formatAccumulatedReturn, normaliseSaxoPerformance, saxoMonthPerformanceQuery } from "./performance.ts";

test("month performance query is one read-only timeseries", () => {
  const query = saxoMonthPerformanceQuery("client-key");
  assert.equal(query.startsWith("/hist/v4/performance/timeseries?"), true);
  assert.equal(query.includes("StandardPeriod=Month"), true);
  assert.equal(query.includes("Balance_AccountValue"), true);
  assert.equal(query.includes("TimeWeighted_Accumulated"), true);
  assert.equal(query.includes("MockData"), false);
});

test("accumulated return is a fraction and account value stays a separate series", () => {
  const series = normaliseSaxoPerformance({
    retrievedAt: "2026-10-18T08:00:00.000Z",
    fieldGroups: ["Balance_AccountValue", "TimeWeighted_Accumulated"],
    body: {
      Currency: "SGD",
      Balance: {
        AccountValue: [
          { Date: "2026-10-01", Value: 100 },
          { Date: "2026-10-02", Value: 110 },
        ],
      },
      TimeWeighted: {
        Accumulated: [
          { Date: "2026-10-01", Value: 0 },
          { Date: "2026-10-02", Value: -0.0407 },
        ],
      },
    },
  });
  assert.equal(series?.returnUnit, "fraction");
  assert.equal(series?.scope, "client");
  assert.equal(series?.period, "Month");
  assert.equal(series?.currency, "SGD");
  assert.equal(series?.accountValue.length, 2);
  assert.equal(formatAccumulatedReturn(series?.timeWeightedAccumulated.at(-1)?.value ?? null), "-4.1%");
  assert.equal(
    normaliseSaxoPerformance({
      retrievedAt: "2026-10-18T08:00:00.000Z",
      fieldGroups: ["TimeWeighted_Accumulated"],
      body: { TimeWeighted: { Accumulated: [{ Date: "2026-10-02", Value: 12 }] } },
    }),
    null,
  );
});
