import assert from "node:assert/strict";
import test from "node:test";

import {
  allocateExternalContribution,
  consolidate,
  holdingsAfterRefresh,
  monetaryGaps,
  parseAssetClass,
  targetsAfterResearch,
} from "./allocation.ts";
import { convertMinor, formatMinor, parseMajorToMinor } from "./money.ts";

const targets = [
  { assetClass: "global_equity" as const, targetWeightBps: 6000 },
  { assetClass: "thematic_technology" as const, targetWeightBps: 1000 },
  { assetClass: "investment_grade_bonds" as const, targetWeightBps: 2000 },
  { assetClass: "cash_investable" as const, targetWeightBps: 1000 },
];

test("unknown classification is rejected", () => {
  assert.throws(() => parseAssetClass("equities"), /unknown asset class/);
});

test("invalid target weights are rejected", () => {
  assert.throws(
    () =>
      monetaryGaps(
        [{ assetClass: "global_equity", currentMinor: 0n }],
        [{ assetClass: "global_equity", targetWeightBps: 9000 }],
        0n,
      ),
    /10000/,
  );
});

test("missing fx prevents a combined total", () => {
  const result = consolidate(
    [
      { assetClass: "global_equity", environment: "live", currency: "USD", amountMinor: 10000n },
      { assetClass: "cash_investable", environment: "live", currency: "SGD", amountMinor: 5000n },
    ],
    "SGD",
    [],
    convertMinor,
  );
  assert.equal(result.status, "unavailable");
});

test("dated fx permits a consolidated total", () => {
  const result = consolidate(
    [{ assetClass: "global_equity", environment: "live", currency: "USD", amountMinor: 10000n }],
    "SGD",
    [{ baseCurrency: "USD", quoteCurrency: "SGD", rate: "1.35" }],
    convertMinor,
  );
  assert.deepEqual(result, { status: "total", currency: "SGD", amountMinor: 13500n });
});

test("emergency reserve and simulation are outside the investable total", () => {
  const result = consolidate(
    [
      { assetClass: "emergency_reserve", environment: "live", currency: "SGD", amountMinor: 999n },
      { assetClass: "global_equity", environment: "simulation", currency: "SGD", amountMinor: 999n },
      { assetClass: "global_equity", environment: "live", currency: "SGD", amountMinor: 1000n },
    ],
    "SGD",
    [],
    convertMinor,
  );
  assert.deepEqual(result, { status: "total", currency: "SGD", amountMinor: 1000n });
});

test("external contribution uses monetary gaps and reconciles", () => {
  const classes = [
    { assetClass: "global_equity" as const, currentMinor: 5000n },
    { assetClass: "cash_investable" as const, currentMinor: 0n },
  ];
  const plan = [
    { assetClass: "global_equity" as const, targetWeightBps: 5000 },
    { assetClass: "cash_investable" as const, targetWeightBps: 5000 },
  ];
  const gaps = monetaryGaps(classes, plan, 5000n);
  assert.equal(gaps.find((gap) => gap.assetClass === "cash_investable")?.gapMinor, 5000n);
  const allocated = allocateExternalContribution(classes, plan, 5000n);
  const sum = allocated.reduce((total, row) => total + row.amountMinor, 0n);
  assert.equal(sum, 5000n);
});

test("cash already counted is not treated as a new contribution", () => {
  const classes = [
    { assetClass: "global_equity" as const, currentMinor: 5000n },
    { assetClass: "cash_investable" as const, currentMinor: 5000n },
  ];
  const plan = [
    { assetClass: "global_equity" as const, targetWeightBps: 5000 },
    { assetClass: "cash_investable" as const, targetWeightBps: 5000 },
  ];
  const gaps = monetaryGaps(classes, plan, 0n);
  assert.ok(gaps.every((gap) => gap.gapMinor === 0n));
});

test("research does not change targets", () => {
  const next = targetsAfterResearch(targets);
  assert.deepEqual(next, targets);
  next[0].targetWeightBps = 1;
  assert.equal(targets[0].targetWeightBps, 6000);
});

test("a failed refresh keeps the last snapshot", () => {
  const previous = [{ id: "last-good" }];
  assert.equal(holdingsAfterRefresh(previous, { status: "failed" }), previous);
  assert.deepEqual(holdingsAfterRefresh(previous, { status: "accepted", next: [] }), []);
});

test("minor units reject extra precision and format native currency", () => {
  assert.equal(parseMajorToMinor("10.50", "SGD"), 1050n);
  assert.throws(() => parseMajorToMinor("10.555", "SGD"), /decimal/);
  assert.equal(formatMinor(1050n, "SGD"), "SGD 10.50");
});
