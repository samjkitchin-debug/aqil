import assert from "node:assert/strict";
import test from "node:test";

import type { MacroEventInput, ThemeAssessmentInput } from "./macro-event-types.ts";
import {
  evidenceStatusLine,
  materialDevelopments,
  measureLine,
  PLAUSIBLE_CHANNEL_LABEL,
  presentMacroIntelligence,
  presentedCopy,
  plausibleChannelHref,
  RESEARCH_AWARENESS_LINE,
} from "./present-macro-events.ts";

const AS_OF = new Date("2026-10-24T12:00:00.000Z");

function event(partial: Partial<MacroEventInput> = {}): MacroEventInput {
  return {
    eventId: "11111111-1111-4111-8111-111111111111",
    eventKey: "ustr_section_301_china_continuation_2026",
    category: "trade_policy",
    epistemicClass: "confirmed_event",
    claimScope: "policy_action_stated",
    summary: "USTR states that the actions remain in effect.",
    eventOn: "2026-08-23",
    eventDatesStated: "6 July 2026 and 23 August 2026",
    indicatorSourceIds: ["bls_cpi_u_all_items"],
    channelNote: "CPI-U is a plausible channel, not a measured effect.",
    surfaceOnToday: true,
    surfaceReason: "USTR states that the actions did not terminate and remain in effect.",
    surfacedAt: "2026-10-24T12:00:00.000Z",
    recordClass: "recorded",
    investmentImplication: "no_action",
    evidence: [
      {
        role: "primary",
        clusterKey: "fr-2026-20510",
        title: "Continuation of actions",
        canonicalUrl: "https://www.govinfo.gov/content/pkg/FR-2026-10-07/html/2026-20510.htm",
        publishedAt: "2026-10-07T00:00:00.000Z",
        sourceId: "govinfo_federal_register",
      },
    ],
    ...partial,
  };
}

function theme(partial: Partial<ThemeAssessmentInput> = {}): ThemeAssessmentInput {
  return {
    assessmentId: "22222222-2222-4222-8222-222222222222",
    recordedAt: "2026-10-24T12:00:00.000Z",
    supersedesAssessmentId: null,
    recordClass: "recorded",
    realEconomyActivity:
      "Company-wide actual capital expenditure. This does not establish AI-only spending.",
    earnings: "This does not establish revenue or earnings.",
    marketPrices: "This does not establish equity prices.",
    mediaAttention: "This does not establish whether the theme is accelerating.",
    dimensions: [
      {
        dimension: "infrastructure_investment",
        status: "available",
        measureKind: "actual_capital_expenditure",
        explanation: "Company-wide actual capital expenditure for one annual period.",
        amount: "10",
        unit: "USD",
        periodStart: "2024-07-01",
        periodEnd: "2025-06-30",
        reportingEntity: "Example entity",
        relationship: "supports",
        sourceUrl: "https://www.sec.gov/Archives/edgar/data/789019/example-index.html",
      },
      {
        dimension: "commercial_adoption",
        status: "not_yet_monitored",
        measureKind: "none",
        explanation: "A customer adoption observation is still required.",
        amount: null,
        unit: null,
        periodStart: null,
        periodEnd: null,
        reportingEntity: null,
        relationship: null,
        sourceUrl: null,
      },
      {
        dimension: "market_breadth_relative_performance",
        status: "contradictory",
        measureKind: "equity_price",
        explanation: "The stored prices do not agree.",
        amount: null,
        unit: null,
        periodStart: null,
        periodEnd: null,
        reportingEntity: null,
        relationship: "contradicts",
        sourceUrl: null,
      },
    ],
    ...partial,
  };
}

test("missing and contradictory evidence use those words", () => {
  assert.match(evidenceStatusLine("insufficient"), /missing/);
  assert.match(evidenceStatusLine("not_yet_monitored"), /missing/);
  assert.match(evidenceStatusLine("contradictory"), /contradictory/);
});

test("presentation has no ETF or allocation sentence", () => {
  const page = presentMacroIntelligence([event()], [theme()], "evidence", AS_OF);
  const copy = presentedCopy(page);
  assert.equal(page.awareness, RESEARCH_AWARENESS_LINE);
  assert.doesNotMatch(copy, /\bETF\b/i);
  assert.doesNotMatch(copy, /allocation/i);
});

test("price evidence is not described as the health of the technological trend", () => {
  const line = measureLine("equity_price");
  assert.match(line, /equity price/i);
  assert.doesNotMatch(line, /health of the technological trend/i);
  const page = presentMacroIntelligence([], [theme()], "evidence", AS_OF);
  assert.doesNotMatch(presentedCopy(page), /health of the technological trend/i);
});

test("Today keeps the theme and a publication record off the page", () => {
  const publication = event({
    eventKey: "fed_publication_recorded",
    claimScope: "publication_recorded",
    surfaceOnToday: false,
    surfaceReason: null,
    recordClass: "recorded",
  });
  const synthetic = event({
    eventKey: "synthetic_only_event",
    recordClass: "synthetic_fixture",
  });
  const page = presentMacroIntelligence(
    [event(), publication, synthetic],
    [theme()],
    "today",
    AS_OF,
  );
  assert.deepEqual(
    page.events.map((item) => item.eventKey),
    ["ustr_section_301_china_continuation_2026"],
  );
  assert.equal(page.themes.length, 0);
  assert.equal(page.events[0]?.sourceLabel, "Federal Register via govinfo");
  assert.match(page.events[0]?.datesStated ?? "", /6 July 2026/);
  assert.match(page.events[0]?.publishedDate ?? "", /7 October 2026/);
});

test("a date outside 45 days is not a material development", () => {
  const old = event({
    eventOn: "2020-01-01",
    evidence: [
      {
        role: "primary",
        clusterKey: "old",
        title: "Old notice",
        canonicalUrl: "https://example.test/old",
        publishedAt: "2020-01-02T00:00:00.000Z",
        sourceId: "govinfo_federal_register",
      },
    ],
  });
  assert.equal(materialDevelopments([old], AS_OF).length, 0);
});

test("synthetic fixtures are not presented", () => {
  const page = presentMacroIntelligence(
    [event({ recordClass: "synthetic_fixture" })],
    [theme({ recordClass: "synthetic_fixture" })],
    "evidence",
    AS_OF,
  );
  assert.equal(page.events.length, 0);
  assert.equal(page.themes.length, 0);
});

test("channel links use the macro panel anchor", () => {
  assert.equal(
    plausibleChannelHref("bls_cpi_u_all_items"),
    "/conditions#macro-panel-bls_cpi_u_all_items",
  );
  assert.equal(PLAUSIBLE_CHANNEL_LABEL, "Plausible channel");
});

test("a superseded assessment stays visible", () => {
  const prior = theme({ assessmentId: "prior" });
  const next = theme({
    assessmentId: "next",
    recordedAt: "2026-10-25T12:00:00.000Z",
    supersedesAssessmentId: "prior",
  });
  const page = presentMacroIntelligence([], [next, prior], "evidence", AS_OF);
  assert.deepEqual(
    page.themes.map((item) => item.assessmentId),
    ["prior", "next"],
  );
  assert.match(page.themes[0]?.supersededLine ?? "", /superseded/);
  assert.equal(page.themes[1]?.supersededLine, null);
});
