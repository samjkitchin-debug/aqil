import assert from "node:assert/strict";
import test from "node:test";

import {
  ETF_EMPTY_COPY,
  ETF_RESEARCH_BOUNDARY,
  HOLDINGS_BLOCKED_REASON,
  assessmentCopy,
  benchmarkCopy,
  costsCopy,
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
  };
}

test("the empty catalogue does not claim a verified fund", () => {
  assert.match(ETF_EMPTY_COPY, /IE00BK5BQT80/);
  assert.match(ETF_EMPTY_COPY, /not a permitted issuer citation/);
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
});
