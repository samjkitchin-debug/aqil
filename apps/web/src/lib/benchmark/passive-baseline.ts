import { createHash } from "node:crypto";

import {
  compareCashflowMatchedPassive,
  type CashflowMatchedComparison,
  type CashflowMatchedInput,
} from "./cashflow-matched.ts";
import {
  validateMethodCardForRegistry,
  type MethodCard,
} from "./method-card-contract.ts";

export const PASSIVE_BASELINE_METHOD_ID = "PASSIVE_CASHFLOW_BASELINE";
export const PASSIVE_BASELINE_METHOD_VERSION = "1.0.0";

const FORMULA =
  "Convert each external cashflow into the benchmark currency with the caller-supplied foreign-exchange rate on that same date, using identity when the currencies already match. After conversion, reduce a contribution by the entry cost in basis points and buy units at the benchmark level on that date. For a withdrawal, increase the units sold by the exit cost so the net matches the converted withdrawal, at the level on that date. Apply contributions before withdrawals on the same date. Ending passive value equals remaining units times the level on the valuation date, converted into the reporting currency with the rate on that date. Round half-units away from zero. If a level, rate, cost, or sufficient unit balance is missing, leave the comparison unavailable and substitute nothing.";

/** SHA-256 of the method id and version. Not a hash of a price series. */
export function passiveBaselineImplementationHash(): string {
  return createHash("sha256")
    .update(`${PASSIVE_BASELINE_METHOD_ID}:${PASSIVE_BASELINE_METHOD_VERSION}`)
    .digest("hex");
}

/**
 * Method card for the passive baseline. Fields follow the research MethodCard contract.
 * Evidence is "implemented": the arithmetic is deterministic. No historical index is claimed.
 */
export function passiveBaselineMethodCard(): MethodCard {
  return {
    schema_version: "1.0",
    method_id: PASSIVE_BASELINE_METHOD_ID,
    method_version: PASSIVE_BASELINE_METHOD_VERSION,
    name: "Cashflow-matched passive baseline",
    research_question:
      "What ending value would the same external cashflows have produced in the caller-supplied passive benchmark after the stated costs and foreign exchange?",
    primary_reference:
      "Aqil docs/04_ARCHITECTURE_AND_DATA.md portfolio journal section and architecture decision 010: the same external flows and timing, with a prescribed execution, foreign-exchange and cost policy.",
    original_universe:
      "Caller-supplied total-return benchmark series and external portfolio cashflows. This method does not select an index.",
    original_horizon: null,
    formula_specification: FORMULA,
    data_requirements: [
      "External cashflows with a date, signed minor units and a currency",
      "A total-return benchmark level on each cashflow date and on the valuation date",
      "A foreign-exchange rate on each date where the currencies differ, in the required direction",
      "Explicit entry and exit cost basis points",
      "A portfolio ending value already denominated in reporting-currency minor units",
    ],
    assumptions: [
      "Supplied cashflows are external flows",
      "Execution is at the supplied level on the cashflow date",
      "Costs are basis points in the benchmark currency after conversion",
      "A supplied zero cost is an explicit assumption",
    ],
    limitations: [
      "No rate of return is calculated",
      "Missing levels and rates are not interpolated, inverted or carried forward",
      "A broad equity index is a comparable strategy only when the caller supplies that series",
      "The value difference is not a forecast and not advice",
      "Historical index reproduction is not claimed",
    ],
    evidence_stage: "implemented",
    implementation_hash: passiveBaselineImplementationHash(),
    licence_status: "permitted_private",
    reviewer_id: null,
  };
}

export type PassiveBaselineCalculation = {
  passiveEndingValueMinor: bigint;
  portfolioEndingValueMinor: bigint;
  valueDifferenceMinor: bigint;
  passiveUnits: string;
  valuationDate: string;
  reportingCurrency: string;
  benchmarkCurrency: string;
  entryCostBps: string;
  exitCostBps: string;
  execution: "same-day";
};

export type PassiveBaselineResult = {
  methodId: string;
  methodVersion: string;
  implementationHash: string;
  sufficiency: "sufficient" | "insufficient";
  calculation: PassiveBaselineCalculation | null;
  assumptions: readonly string[];
  limitations: readonly string[];
  missingReason: string | null;
  statisticalInterpretation: string;
  causalHypothesis: string;
  investmentImplication: "no_action" | "insufficient_evidence";
  narrative: string;
};

/**
 * Passive baseline (AQ-031). Uses the cashflow-matched comparison and the method-card contract.
 * An unavailable comparison does not become a return.
 */
export function runPassiveBaseline(input: CashflowMatchedInput): PassiveBaselineResult {
  const card = passiveBaselineMethodCard();
  validateMethodCardForRegistry(card);
  const comparison = compareCashflowMatchedPassive(input);
  if (comparison.status === "unavailable") {
    return {
      methodId: card.method_id,
      methodVersion: card.method_version,
      implementationHash: card.implementation_hash ?? passiveBaselineImplementationHash(),
      sufficiency: "insufficient",
      calculation: null,
      assumptions: card.assumptions,
      limitations: card.limitations,
      missingReason: comparison.reason,
      statisticalInterpretation: "The comparison was not run because a required input was missing or did not match.",
      causalHypothesis: "No causal mechanism is asserted.",
      investmentImplication: "insufficient_evidence",
      narrative: `${comparison.reason} No rate of return is substituted.`,
    };
  }
  return {
    methodId: card.method_id,
    methodVersion: card.method_version,
    implementationHash: card.implementation_hash ?? passiveBaselineImplementationHash(),
    sufficiency: "sufficient",
    calculation: calculationFrom(comparison),
    assumptions: [...card.assumptions, ...comparison.assumptions],
    limitations: card.limitations,
    missingReason: null,
    statisticalInterpretation:
      "This is a cashflow-matched value comparison. It is not a rate of return, a forecast, or a risk benchmark.",
    causalHypothesis: "No causal mechanism is asserted.",
    investmentImplication: "no_action",
    narrative: narrativeFrom(comparison),
  };
}

function calculationFrom(comparison: Extract<CashflowMatchedComparison, { status: "available" }>): PassiveBaselineCalculation {
  return {
    passiveEndingValueMinor: comparison.passiveEndingValueMinor,
    portfolioEndingValueMinor: comparison.portfolioEndingValueMinor,
    valueDifferenceMinor: comparison.valueDifferenceMinor,
    passiveUnits: comparison.passiveUnits,
    valuationDate: comparison.valuationDate,
    reportingCurrency: comparison.reportingCurrency,
    benchmarkCurrency: comparison.benchmarkCurrency,
    entryCostBps: comparison.costs.entryCostBps,
    exitCostBps: comparison.costs.exitCostBps,
    execution: comparison.execution,
  };
}

function narrativeFrom(comparison: Extract<CashflowMatchedComparison, { status: "available" }>): string {
  return [
    `Passive ending value on ${comparison.valuationDate} is ${comparison.passiveEndingValueMinor} minor units of ${comparison.reportingCurrency}.`,
    `Portfolio ending value is ${comparison.portfolioEndingValueMinor} minor units.`,
    `Value difference is ${comparison.valueDifferenceMinor} minor units.`,
    "This is not a rate of return.",
  ].join(" ");
}
