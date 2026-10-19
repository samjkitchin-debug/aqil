import assert from "node:assert/strict";
import test from "node:test";

import {
  additionalCashMinorFromMajor,
  assertPolicyTargets,
  parseAdditionalCashMajor,
  parseStoredPolicy,
  targetsFromPercentFields,
} from "./policy.ts";

test("targets that do not total 10000 basis points are rejected on save", () => {
  const targets = targetsFromPercentFields({
    global_equity: "60",
    thematic_technology: "0",
    investment_grade_bonds: "0",
    cash_investable: "0",
  });
  assert.throws(() => assertPolicyTargets(targets), /10000/);
});

test("a blank budget stays not configured", () => {
  assert.equal(parseAdditionalCashMajor(""), null);
  assert.equal(parseAdditionalCashMajor("   "), null);
  assert.equal(parseAdditionalCashMajor(undefined), null);
  const stored = parseStoredPolicy({
    version: 1,
    targets: [{ assetClass: "global_equity", targetWeightBps: 10000 }],
    additionalCashMajor: null,
    instruments: [],
    holdingClasses: {},
  });
  assert.equal(stored?.additionalCashMajor, null);
  assert.equal(additionalCashMinorFromMajor(null, "SGD"), null);
});
