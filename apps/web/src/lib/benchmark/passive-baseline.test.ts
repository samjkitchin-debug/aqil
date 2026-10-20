import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import test from "node:test";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { compareCashflowMatchedPassive } from "./cashflow-matched.ts";
import { validateMethodCardForRegistry } from "./method-card-contract.ts";
import {
  PASSIVE_BASELINE_METHOD_ID,
  PASSIVE_BASELINE_METHOD_VERSION,
  passiveBaselineImplementationHash,
  passiveBaselineMethodCard,
  runPassiveBaseline,
} from "./passive-baseline.ts";

const registryPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../../../../workers/research/src/aqil_research/methods/card_registry.py",
);
const methodCardPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../../../../workers/research/src/aqil_research/contracts/method_card.py",
);

test("passive baseline card meets the research method-card contract", () => {
  const registry = readFileSync(registryPath, "utf8");
  const contract = readFileSync(methodCardPath, "utf8");
  assert.match(registry, /def validate_method_card_for_registry/);
  for (const label of ["origin", "universe", "equation", "limitations", "rights"]) {
    assert.match(registry, new RegExp(`missing\\.append\\("${label}"\\)`));
  }
  for (const field of [
    "primary_reference",
    "original_universe",
    "formula_specification",
    "limitations",
    "licence_status",
  ]) {
    assert.match(contract, new RegExp(`\\b${field}\\b`));
  }

  const card = passiveBaselineMethodCard();
  assert.doesNotThrow(() => validateMethodCardForRegistry(card));
  assert.equal(card.method_id, PASSIVE_BASELINE_METHOD_ID);
  assert.equal(card.method_version, PASSIVE_BASELINE_METHOD_VERSION);
  assert.equal(card.evidence_stage, "implemented");
  assert.equal(card.licence_status, "permitted_private");
  assert.equal(card.implementation_hash, passiveBaselineImplementationHash());
  assert.equal(
    card.implementation_hash,
    createHash("sha256").update(`${PASSIVE_BASELINE_METHOD_ID}:${PASSIVE_BASELINE_METHOD_VERSION}`).digest("hex"),
  );
});

test("registry contract rejects an incomplete passive baseline card", () => {
  const card = passiveBaselineMethodCard();
  assert.throws(() => validateMethodCardForRegistry({ ...card, primary_reference: " " }), /origin/);
  assert.throws(() => validateMethodCardForRegistry({ ...card, original_universe: "" }), /universe/);
  assert.throws(() => validateMethodCardForRegistry({ ...card, formula_specification: null }), /equation/);
  assert.throws(() => validateMethodCardForRegistry({ ...card, limitations: [" "] }), /limitations/);
  assert.throws(() => validateMethodCardForRegistry({ ...card, licence_status: "unknown" }), /rights/);
});

test("passive baseline does not invent a result when inputs are omitted", () => {
  const result = runPassiveBaseline({
    cashflows: undefined,
    benchmarkSeries: undefined,
    fx: undefined,
    costs: undefined,
    valuationDate: undefined,
    reportingCurrency: undefined,
    portfolioEndingValueMinor: undefined,
  });
  assert.equal(result.sufficiency, "insufficient");
  assert.equal(result.calculation, null);
  assert.equal(result.investmentImplication, "insufficient_evidence");
  assert.equal(result.missingReason, "Benchmark series was not supplied.");
  assert.match(result.narrative, /No rate of return is substituted/);
  assert.doesNotMatch(result.narrative, /%/);
});

test("passive baseline reproduces the cashflow-matched comparison and no return rate", () => {
  const input = {
    cashflows: [
      {
        cashflowId: "contribution-1",
        occurredOn: "2024-03-01",
        amountMinor: 10_000n,
        currency: "SGD",
      },
    ],
    benchmarkSeries: [
      { occurredOn: "2024-03-01", level: "74.00", currency: "USD" },
      { occurredOn: "2024-04-01", level: "80.00", currency: "USD" },
    ],
    fx: {
      rates: [
        {
          occurredOn: "2024-03-01",
          baseCurrency: "SGD",
          quoteCurrency: "USD",
          rate: "0.74",
        },
      ],
    },
    costs: { entryCostBps: "100", exitCostBps: "0" },
    valuationDate: "2024-04-01",
    reportingCurrency: "USD",
    portfolioEndingValueMinor: 8_000n,
  };
  const comparison = compareCashflowMatchedPassive(input);
  const result = runPassiveBaseline(input);
  assert.equal(comparison.status, "available");
  if (comparison.status !== "available") return;
  assert.equal(result.sufficiency, "sufficient");
  assert.equal(result.methodId, PASSIVE_BASELINE_METHOD_ID);
  assert.equal(result.investmentImplication, "no_action");
  assert.equal(result.calculation?.passiveEndingValueMinor, comparison.passiveEndingValueMinor);
  assert.equal(result.calculation?.portfolioEndingValueMinor, comparison.portfolioEndingValueMinor);
  assert.equal(result.calculation?.valueDifferenceMinor, comparison.valueDifferenceMinor);
  assert.equal(result.calculation?.passiveUnits, "0.99000000");
  assert.equal(result.calculation?.entryCostBps, "100");
  assert.equal(result.calculation?.exitCostBps, "0");
  assert.equal(result.calculation?.execution, "same-day");
  assert.equal("rateOfReturn" in (result.calculation ?? {}), false);
  assert.match(result.narrative, /This is not a rate of return/);
  assert.match(result.assumptions.join(" "), /100 basis points/);
  assert.match(result.limitations.join(" "), /No rate of return is calculated/);
});
