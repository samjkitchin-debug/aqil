import assert from "node:assert/strict";
import test from "node:test";

import { validateForwardHorizon } from "./validate-forward-horizon.ts";

function validBundle(): Record<string, unknown> {
  return {
    schema_version: "1.0",
    generated_at: "2026-10-17T10:00:00+00:00",
    data_mode: "mixed",
    etfs: [
      {
        etf_id: "etf:demo",
        legal_name: "Demonstration ETF",
        ticker: "DEMO",
        exchange: "LSE",
        isin: "IE00BK5BQT80",
        identity_evidence: "verified_instrument_identity",
        holdings_as_of: "2025-06-30",
        completeness: "top_holdings_partial",
        holdings_evidence: "synthetic_demonstration",
        holdings_caveat: "Weights are synthetic demonstration data, not fund-provider holdings.",
        top_holdings: [{ name: "Microsoft Corp", weight_percentage: "4.20" }],
      },
    ],
    events: [
      {
        event_id: "event:fixture:msft",
        title: "Earnings (fixture)",
        category: "company_earnings",
        scheduled_date: "2026-01-28",
        date_precision: "estimated",
        schedule_evidence: "synthetic_demonstration",
        materiality: "insufficient_evidence",
        materiality_basis: "calculated",
        interpretation_status: "unverified",
        why_it_matters: "Synthetic weight only.",
        is_fixture: true,
      },
      {
        event_id: "event:verified:fed",
        title: "FOMC meeting",
        category: "central_bank_meeting",
        scheduled_date: "2025-09-17",
        date_precision: "confirmed",
        schedule_evidence: "verified_schedule",
        materiality: "insufficient_evidence",
        materiality_basis: "insufficient_evidence",
        interpretation_status: "unverified",
        why_it_matters: "Schedule only.",
        is_fixture: false,
      },
    ],
    exposures: [
      {
        event_id: "event:fixture:msft",
        etf_id: "etf:demo",
        issuer_id: "issuer:msft",
        weight_percentage: "4.20",
        weight_evidence: "synthetic_demonstration",
        materiality: "insufficient_evidence",
        materiality_evidence: "calculated",
      },
    ],
    scenarios: [
      {
        scenario_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        event_id: "event:fixture:msft",
        frozen_at: "2026-01-20T12:00:00+00:00",
        headline: "Fixture scenario",
        evidence_class: "synthetic_demonstration",
      },
    ],
    outcomes: [
      {
        outcome_id: "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff",
        event_id: "event:fixture:msft",
        scenario_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        headline: "Fixture outcome",
        evidence_class: "synthetic_demonstration",
      },
    ],
  };
}

test("accepts a labelled mixed bundle", () => {
  assert.equal(validateForwardHorizon(validBundle()), true);
});

test("rejects malformed json objects", () => {
  assert.equal(validateForwardHorizon(null), false);
  assert.equal(validateForwardHorizon({ schema_version: "1.0" }), false);
});

test("rejects a fixture event presented as a verified schedule", () => {
  const bundle = validBundle();
  const events = bundle.events as Record<string, unknown>[];
  events[0].schedule_evidence = "verified_schedule";
  events[0].date_precision = "confirmed";
  assert.equal(validateForwardHorizon(bundle), false);
});

test("rejects synthetic holdings presented as verified source data", () => {
  const bundle = validBundle();
  bundle.data_mode = "verified_source";
  assert.equal(validateForwardHorizon(bundle), false);
});

test("rejects an outcome that does not reference a scenario", () => {
  const bundle = validBundle();
  const outcomes = bundle.outcomes as Record<string, unknown>[];
  outcomes[0].scenario_id = "00000000-0000-4000-8000-000000000000";
  assert.equal(validateForwardHorizon(bundle), false);
});

test("rejects a verified schedule with an unconfirmed date", () => {
  const bundle = validBundle();
  const events = bundle.events as Record<string, unknown>[];
  events[1].date_precision = "estimated";
  assert.equal(validateForwardHorizon(bundle), false);
});

test("rejects synthetic weights labelled as provider holdings", () => {
  const bundle = validBundle();
  const exposures = bundle.exposures as Record<string, unknown>[];
  exposures[0].weight_evidence = "provider_holdings";
  assert.equal(validateForwardHorizon(bundle), false);
});
