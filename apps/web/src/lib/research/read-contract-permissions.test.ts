import assert from "node:assert/strict";
import test from "node:test";

import { METHOD_PERMISSIONS, permissionFor } from "./read-contract-permissions.ts";
import { RESEARCH_READ_CONTRACT_VERSION } from "./read-contract-types.ts";

test("the read contract is version 2 and nothing is published", () => {
  assert.equal(RESEARCH_READ_CONTRACT_VERSION, "2");
  assert.equal(METHOD_PERMISSIONS.length, 26);
  assert.equal(METHOD_PERMISSIONS.every((row) => row.publicationAllowed === false), true);
  assert.equal(METHOD_PERMISSIONS.some((row) => row.consumerUse === "qualified_forecast"), false);
});

test("an unexpected method id is not given a use", () => {
  assert.equal(permissionFor("NOT_A_METHOD"), null);
});

test("a blocked method stays blocked and a descriptive method is not asked to forecast", () => {
  assert.equal(permissionFor("SAHM_UNEMPLOYMENT_GAP")?.consumerUse, "blocked");
  assert.equal(permissionFor("INFLATION_AUTOREGRESSION")?.consumerUse, "blocked");
  assert.equal(permissionFor("ESTRELLA_MISHKIN_TERM_SPREAD")?.consumerUse, "descriptive_measurement");
  assert.equal(permissionFor("HAMILTON_MONTHLY_REGIME_SWITCHING")?.consumerUse, "experimental_only");
});
