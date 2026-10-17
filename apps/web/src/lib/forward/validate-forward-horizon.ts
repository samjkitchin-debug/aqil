import type { ForwardHorizonV1 } from "@/lib/forward/types";

const MATERIALITY = new Set(["high", "medium", "low", "insufficient_evidence"]);
const DATE_PRECISION = new Set(["confirmed", "estimated", "tentative", "unknown"]);
const DATA_MODE = new Set(["fixture_demonstration", "verified_source", "mixed"]);

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasString(row: Record<string, unknown>, key: string): boolean {
  return typeof row[key] === "string" && row[key] !== "";
}

export function validateForwardHorizon(data: unknown): data is ForwardHorizonV1 {
  if (!isObject(data)) return false;
  if (data.schema_version !== "1.0") return false;
  if (!hasString(data, "generated_at")) return false;
  if (typeof data.data_mode !== "string" || !DATA_MODE.has(data.data_mode)) return false;
  if (!Array.isArray(data.etfs) || !Array.isArray(data.events) || !Array.isArray(data.exposures)) {
    return false;
  }

  for (const etf of data.etfs) {
    if (!isObject(etf)) return false;
    if (!hasString(etf, "etf_id") || !hasString(etf, "legal_name") || !hasString(etf, "ticker")) {
      return false;
    }
    if (!hasString(etf, "exchange") || !hasString(etf, "holdings_as_of") || !hasString(etf, "completeness")) {
      return false;
    }
    if (etf.identity_evidence !== "verified_instrument_identity" && etf.identity_evidence !== "unverified") {
      return false;
    }
    if (
      etf.holdings_evidence !== "synthetic_demonstration" &&
      etf.holdings_evidence !== "provider_holdings" &&
      etf.holdings_evidence !== "not_available"
    ) {
      return false;
    }
    if (!hasString(etf, "holdings_caveat")) return false;
    if (data.data_mode === "verified_source" && etf.holdings_evidence !== "provider_holdings") {
      return false;
    }
    if (
      etf.holdings_evidence === "synthetic_demonstration" &&
      etf.identity_evidence === "verified_instrument_identity" &&
      !String(etf.holdings_caveat).toLowerCase().includes("synthetic")
    ) {
      return false;
    }
    if (!Array.isArray(etf.top_holdings)) return false;
    for (const line of etf.top_holdings) {
      if (!isObject(line) || !hasString(line, "name") || !hasString(line, "weight_percentage")) {
        return false;
      }
    }
  }

  for (const event of data.events) {
    if (!isObject(event)) return false;
    if (!hasString(event, "event_id") || !hasString(event, "title") || !hasString(event, "category")) {
      return false;
    }
    if (!hasString(event, "scheduled_date") || !hasString(event, "why_it_matters")) return false;
    if (typeof event.date_precision !== "string" || !DATE_PRECISION.has(event.date_precision)) {
      return false;
    }
    if (typeof event.materiality !== "string" || !MATERIALITY.has(event.materiality)) return false;
    if (
      event.materiality_basis !== "calculated" &&
      event.materiality_basis !== "insufficient_evidence" &&
      event.materiality_basis !== "macro_qualitative"
    ) {
      return false;
    }
    if (event.interpretation_status !== "unverified") return false;
    if (
      event.schedule_evidence !== "verified_schedule" &&
      event.schedule_evidence !== "verified_announcement" &&
      event.schedule_evidence !== "synthetic_demonstration" &&
      event.schedule_evidence !== "unverified"
    ) {
      return false;
    }
    if (event.is_fixture === true && event.schedule_evidence !== "synthetic_demonstration") {
      return false;
    }
    if (
      event.schedule_evidence === "verified_schedule" ||
      event.schedule_evidence === "verified_announcement"
    ) {
      if (event.date_precision !== "confirmed" || event.is_fixture !== false) return false;
    }
    if (event.materiality_basis === "insufficient_evidence" && event.materiality !== "insufficient_evidence") {
      return false;
    }
  }

  for (const exposure of data.exposures) {
    if (!isObject(exposure)) return false;
    if (!hasString(exposure, "event_id") || !hasString(exposure, "etf_id") || !hasString(exposure, "issuer_id")) {
      return false;
    }
    if (!hasString(exposure, "weight_percentage") || !hasString(exposure, "materiality")) return false;
    if (
      exposure.weight_evidence !== "synthetic_demonstration" &&
      exposure.weight_evidence !== "provider_holdings"
    ) {
      return false;
    }
    if (
      exposure.materiality_evidence !== "calculated" &&
      exposure.materiality_evidence !== "insufficient_evidence"
    ) {
      return false;
    }
    if (exposure.weight_evidence === "synthetic_demonstration" && exposure.materiality_evidence !== "calculated") {
      return false;
    }
    const etf = data.etfs.find(
      (row) => isObject(row) && row.etf_id === exposure.etf_id,
    );
    if (isObject(etf) && etf.holdings_evidence === "synthetic_demonstration") {
      if (exposure.weight_evidence !== "synthetic_demonstration") return false;
    }
  }

  if (data.scenarios !== undefined) {
    if (!Array.isArray(data.scenarios)) return false;
    for (const scenario of data.scenarios) {
      if (!isObject(scenario)) return false;
      if (!hasString(scenario, "scenario_id") || !hasString(scenario, "event_id")) return false;
      if (!hasString(scenario, "frozen_at") || !hasString(scenario, "headline")) return false;
      if (scenario.evidence_class !== "synthetic_demonstration") return false;
    }
  }

  if (data.outcomes !== undefined) {
    if (!Array.isArray(data.outcomes)) return false;
    const scenarioIds = new Set(
      (Array.isArray(data.scenarios) ? data.scenarios : [])
        .filter(isObject)
        .map((row) => row.scenario_id),
    );
    for (const outcome of data.outcomes) {
      if (!isObject(outcome)) return false;
      if (!hasString(outcome, "outcome_id") || !hasString(outcome, "event_id")) return false;
      if (!hasString(outcome, "scenario_id") || !hasString(outcome, "headline")) return false;
      if (outcome.evidence_class !== "synthetic_demonstration") return false;
      if (!scenarioIds.has(outcome.scenario_id)) return false;
    }
  }

  return true;
}
