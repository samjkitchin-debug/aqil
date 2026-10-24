import assert from "node:assert/strict";
import test from "node:test";

import { NOT_INVESTMENT_CONCLUSION } from "../research/present-economic-evidence.ts";
import { MACRO_SERIES } from "../research/macro-conditions.ts";
import { mapCitedExposure } from "./exposure-context.ts";
import {
  ETF_CITED_DOCUMENT_REQUIREMENT,
  ETF_EMPTY_COPY,
  ETF_RESEARCH_BOUNDARY,
  EXPOSURES_ABSENT,
  HOLDINGS_BLOCKED_REASON,
  SHARE_CLASS_ABSENT,
  assessmentCopy,
  benchmarkCopy,
  citedShareClassHref,
  costsCopy,
  exposureCopy,
  holdingsCopy,
  identityCopy,
  listingsCopy,
  type EtfShareExplore,
} from "./present-explore.ts";

function unverifiedAnchor(): EtfShareExplore {
  return {
    isin: "IE00BK5BQT80",
    evidenceStatus: "unverified",
    distributionPolicy: "unknown",
    hedgeStatus: "unknown",
    inceptionDate: null,
    recordedAt: "2026-10-23T04:00:00Z",
    listings: [],
    costs: [],
    holdings: { shown: false, reason: HOLDINGS_BLOCKED_REASON },
    benchmark: { cited: false },
    assessment: {
      eligibility: "UNKNOWN",
      evidenceStatus: "insufficient",
      statement: "Hard evidence is missing, so this share class is not eligible.",
      recordedAt: "2026-10-23T04:00:00Z",
    },
    fundReturnCount: 0,
    benchmarkReturnCount: 0,
    exposures: [],
  };
}

test("the empty catalogue does not claim a verified fund", () => {
  assert.match(ETF_EMPTY_COPY, /No share class is stored/);
  assert.match(ETF_EMPTY_COPY, /IE00BK5BQT80/);
  assert.match(ETF_EMPTY_COPY, /not a permitted issuer citation/);
  assert.match(ETF_CITED_DOCUMENT_REQUIREMENT, /docs\/sources\/etf\/cited\/\*\.json/);
  assert.match(ETF_CITED_DOCUMENT_REQUIREMENT, /source_id/);
  assert.match(ETF_CITED_DOCUMENT_REQUIREMENT, /founder_supplied does not permit/);
  assert.match(ETF_CITED_DOCUMENT_REQUIREMENT, /Unknown and prohibited each refuse/);
  assert.match(ETF_CITED_DOCUMENT_REQUIREMENT, /docs\/sources\/SOURCE_RIGHTS\.csv/);
  assert.match(ETF_CITED_DOCUMENT_REQUIREMENT, /forward-horizon\.v1\.json is not that document/);
  assert.doesNotMatch(ETF_CITED_DOCUMENT_REQUIREMENT, /share class is stored/i);
  assert.doesNotMatch(ETF_CITED_DOCUMENT_REQUIREMENT, /VWRA/);
  assert.match(ETF_RESEARCH_BOUNDARY, /not your broker holdings/);
  assert.match(ETF_RESEARCH_BOUNDARY, /not personal advice/);
});

test("an unverified anchor hides uncited fields and holdings", () => {
  const share = unverifiedAnchor();
  assert.match(identityCopy(share), /unverified/);
  assert.match(identityCopy(share), /not cited/);
  assert.match(listingsCopy(share), /No listing is cited/);
  assert.match(costsCopy(share), /not the total cost/);
  assert.match(costsCopy(share), /No live spread/);
  assert.equal(holdingsCopy(share), HOLDINGS_BLOCKED_REASON);
  assert.match(benchmarkCopy(share), /separate series/);
  assert.match(assessmentCopy(share), /^UNKNOWN/);
  assert.doesNotMatch(assessmentCopy(share), /CORE/);
  assert.equal(share.exposures.length, 0);
});

test("an exact ISIN can open a dossier and a ticker cannot", () => {
  assert.equal(citedShareClassHref(null), null);
  assert.equal(citedShareClassHref(""), null);
  assert.equal(citedShareClassHref("VWRA"), null);
  assert.equal(citedShareClassHref("IE00BK5BQT80"), "/explore?isin=IE00BK5BQT80");
  assert.equal(SHARE_CLASS_ABSENT, "No cited share class is stored for this ISIN.");
  assert.doesNotMatch(SHARE_CLASS_ABSENT, /VWRA/);
  assert.equal(EXPOSURES_ABSENT, "No cited exposure is stored.");
});

test("a cited exposure maps only to stored operational series", () => {
  const known = new Set(MACRO_SERIES.map((series) => series.sourceId));
  const unitedStates = mapCitedExposure("US equity");
  assert.equal(unitedStates.status, "mapped");
  if (unitedStates.status !== "mapped") return;
  assert.ok(unitedStates.series.length > 0);
  for (const series of unitedStates.series) {
    assert.ok(known.has(series.sourceId));
    assert.match(series.href, /\/conditions\?region=united-states#macro-panel-/);
  }
  assert.equal(unitedStates.unitedStatesReading?.sentence, NOT_INVESTMENT_CONCLUSION);
  assert.equal(unitedStates.unitedStatesReading?.href, "/conditions?region=united-states");

  const europe = mapCitedExposure("Europe equity");
  assert.equal(europe.status, "mapped");
  if (europe.status !== "mapped") return;
  assert.equal(europe.unitedStatesReading, null);
  assert.ok(europe.series.every((series) => known.has(series.sourceId)));
  assert.ok(europe.series.every((series) => series.href.includes("region=europe")));

  assert.equal(mapCitedExposure("VWRA").status, "missing");
  assert.deepEqual(mapCitedExposure("Broad technology, healthcare, or financials sector equity"), {
    status: "missing",
    sentence: "No sector series is stored.",
  });
  assert.deepEqual(mapCitedExposure("Quality, value, or minimum-volatility factor equity"), {
    status: "missing",
    sentence: "No factor series is stored.",
  });
  assert.match(exposureCopy({
    exposureClass: "Synthetic geography",
    weightText: null,
    asOf: "2026-01-15",
    sourceId: "fixture_cited_issuer_document",
    sourceLocator: "synthetic://aqil/etf/cited-exposures",
    recordedAt: "2026-01-16T00:00:00Z",
  }), /No weight is cited/);
});
