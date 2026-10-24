export const ETF_RESEARCH_BOUNDARY =
  "ETF research is not your broker holdings and it is not personal advice.";

export const ETF_EMPTY_COPY =
  "No share class is stored. No source is cleared for automated collection, so listings, costs, holdings, and returns stay unavailable. The internal anchor ISIN IE00BK5BQT80 (VWRA) is not a permitted issuer citation.";

/**
 * Founder-facing copy of the cited-document gate in
 * workers/research/src/aqil_research/etf/documents/ingest.py
 * (FIRST_INSERT_REQUIREMENT). No share class is claimed.
 */
export const ETF_CITED_DOCUMENT_REQUIREMENT =
  "A first share-class insert needs one cited issuer document at docs/sources/etf/cited/*.json and a rights row with the same source_id. The document must include source_id, source_locator, and a document_date or retrieved_on, plus isin, umbrella_legal_name, sub_fund_legal_name, base_currency, distribution_policy, and hedge_status. Omitted fields stay absent. founder_supplied does not permit acquire, retain, extract, or display. The rights row must have operational_status enabled, and automated_access (acquire), raw_data_retention (retain), internal_computation (extract), and redistribution (display) must each be permitted. Unknown and prohibited each refuse that use. Do not change an unknown or prohibited cell in docs/sources/SOURCE_RIGHTS.csv to permitted. The internal fixture apps/web/fixtures/forward-horizon.v1.json is not that document. Share classes resolve on instruments.share_classes by ISIN.";

export const HOLDINGS_BLOCKED_REASON =
  "Holdings are not shown. No snapshot with a permitted rights gate is stored, and prohibited or unknown sources are not fetched.";

export type EtfListingView = {
  mic: string;
  tradingCurrency: string;
  ticker: string;
};

export type EtfCostView = {
  code: string;
  availability: "cited" | "unavailable";
  valueText: string | null;
  sourceId: string | null;
};

export type EtfHoldingsView =
  | { shown: false; reason: string }
  | { shown: true; asOf: string; completeness: string; lineCount: number };

export type EtfBenchmarkView =
  | { cited: false }
  | { cited: true; label: string; returnConvention: string; currency: string };

export type EtfAssessmentView = {
  eligibility: "CORE" | "CONDITIONAL" | "EXCLUDED" | "UNKNOWN";
  evidenceStatus: string;
  statement: string;
  recordedAt: string;
};

export type EtfShareExplore = {
  isin: string;
  evidenceStatus: "unverified" | "cited" | "unavailable" | "insufficient";
  distributionPolicy: "accumulating" | "distributing" | "unknown";
  hedgeStatus: "hedged" | "unhedged" | "unknown";
  inceptionDate: string | null;
  recordedAt: string;
  listings: EtfListingView[];
  costs: EtfCostView[];
  holdings: EtfHoldingsView;
  benchmark: EtfBenchmarkView;
  assessment: EtfAssessmentView | null;
  fundReturnCount: number;
  benchmarkReturnCount: number;
};

export function identityCopy(share: EtfShareExplore): string {
  if (share.evidenceStatus !== "cited") {
    return `ISIN ${share.isin} is stored with evidence status ${share.evidenceStatus}. Legal name, domicile, and base currency are not cited.`;
  }
  return `ISIN ${share.isin} is cited.`;
}

export function structureCopy(share: EtfShareExplore): string {
  const inception = share.inceptionDate ?? "unavailable";
  return `Distribution policy ${share.distributionPolicy}. Hedge status ${share.hedgeStatus}. Inception ${inception}. Trading currency belongs to a listing and is not the base currency.`;
}

export function listingsCopy(share: EtfShareExplore): string {
  if (share.listings.length === 0) {
    return "No listing is cited. A ticker change would be identifier history, not a new share class.";
  }
  return share.listings
    .map((listing) => `${listing.ticker} on ${listing.mic} in ${listing.tradingCurrency}`)
    .join("; ");
}

export function costsCopy(share: EtfShareExplore): string {
  const cited = share.costs.filter((cost) => cost.availability === "cited" && cost.valueText);
  if (cited.length === 0) {
    return "Cited costs are unavailable. An issuer-reported TER is not the total cost. No live spread is shown.";
  }
  return cited
    .map((cost) => `${cost.code}: ${cost.valueText} (source ${cost.sourceId ?? "missing"})`)
    .join(". ");
}

export function holdingsCopy(share: EtfShareExplore): string {
  if (!share.holdings.shown) return share.holdings.reason;
  return `Holdings as of ${share.holdings.asOf}. Completeness: ${share.holdings.completeness}. Lines: ${share.holdings.lineCount}. Top-ten overlap is partial.`;
}

export function benchmarkCopy(share: EtfShareExplore): string {
  if (!share.benchmark.cited) {
    return "No benchmark is cited. A benchmark return is a separate series and is not this share class's own return.";
  }
  return `${share.benchmark.label}. Return convention ${share.benchmark.returnConvention}. Currency ${share.benchmark.currency}.`;
}

export function returnsCopy(share: EtfShareExplore): string {
  return `Fund return rows: ${share.fundReturnCount}. Benchmark return rows: ${share.benchmarkReturnCount}. The two series are not interchangeable. A 6, 12, or 24 month fund window is refused before inception and when currency conversion is not cited.`;
}

export function assessmentCopy(share: EtfShareExplore): string {
  if (!share.assessment) {
    return "No eligibility assessment is stored. Missing hard evidence stays unknown. There is no rank.";
  }
  return `${share.assessment.eligibility}. Evidence ${share.assessment.evidenceStatus}. ${share.assessment.statement}`;
}

export function freshnessCopy(share: EtfShareExplore): string {
  return `Share class row recorded ${share.recordedAt}. That timestamp is not a market-data as-of date.`;
}
