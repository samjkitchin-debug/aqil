import assert from "node:assert/strict";
import test from "node:test";

import {
  ILLUSTRATION_DISCLAIMER,
  defaultCompoundingIllustrationInput,
  projectMonthlyCompounding,
  runCompoundingIllustration,
} from "./compounding.ts";

test("illustration disclaimer rejects guaranteed return language", () => {
  assert.match(ILLUSTRATION_DISCLAIMER, /illustration/i);
  assert.match(ILLUSTRATION_DISCLAIMER, /not.*guaranteed return/i);
});

test("contributions and growth reconcile to the nominal ending balance", () => {
  const input = defaultCompoundingIllustrationInput();
  for (const scenario of input.scenarios) {
    const result = projectMonthlyCompounding(input, scenario);
    assert.equal(
      result.totalPaidInMajor + result.growthFromInvestmentsMajor,
      result.nominalEndingMajor,
    );
    assert.equal(
      result.startingBalanceMajor + result.periodicContributionsMajor,
      result.totalPaidInMajor,
    );
  }
});

test("downside, base and favourable illustrations order by nominal ending", () => {
  const { scenarios } = runCompoundingIllustration();
  const byKey = Object.fromEntries(scenarios.map((row) => [row.key, row.nominalEndingMajor]));
  assert.ok(byKey.adverse < byKey.base);
  assert.ok(byKey.base < byKey.favourable);
});

test("fees reduce the net return below the gross assumption", () => {
  const input = defaultCompoundingIllustrationInput();
  const base = projectMonthlyCompounding(
    input,
    input.scenarios.find((row) => row.key === "base")!,
  );
  assert.ok(base.netAnnualReturn < base.grossAnnualReturn);
  assert.equal(base.netAnnualReturn, base.grossAnnualReturn - input.annualFeeRate);
});

test("deterministic base illustration matches the frozen fixture totals", () => {
  const base = runCompoundingIllustration().scenarios.find((row) => row.key === "base")!;
  assert.equal(base.totalPaidInMajor, 53_000);
  assert.equal(base.nominalEndingMajor, 89_967.43);
  assert.equal(base.growthFromInvestmentsMajor, 36_967.43);
  assert.equal(base.inflationAdjustedEndingMajor, 54_904.51);
  assert.equal(base.growthAfterInflationMajor, 1_904.51);
});

test("negative inputs are rejected", () => {
  const input = defaultCompoundingIllustrationInput();
  assert.throws(
    () =>
      projectMonthlyCompounding(
        { ...input, monthlyContributionMajor: -1 },
        input.scenarios[0]!,
      ),
    /monthly contribution/,
  );
});
