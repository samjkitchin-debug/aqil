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
  "A first share-class insert needs one cited issuer document at docs/sources/etf/cited/*.json and a rights row with the same source_id. The document must include source_id, source_locator, and a document_date or retrieved_on, plus isin, umbrella_legal_name, sub_fund_legal_name, base_currency, distribution_policy, and hedge_status. Omitted fields stay absent. founder_supplied does not permit acquire, retain, extract, or display. The rights row must have operational_status enabled, and automated_access (acquire), raw_data_retention (retain), internal_computation (extract), and redistribution (display) must each be permitted. Unknown and prohibited each refuse that use. Do not change an unknown or prohibited cell in docs/sources/SOURCE_RIGHTS.csv to permitted. The internal fixture apps/web/fixtures/forward-horizon.v1.json is not that document. Share classes resolve on instruments.share_classes by ISIN. Optional geographic and sector exposure lines may be included. Each stored line uses evidence_status cited and keeps source_id and source_locator. Trading currency is a listing fact, not an exposure. Holdings files stay out of this path.";

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

export type CitedExposureView = {
  exposureClass: string;
  weightText: string | null;
  asOf: string;
  sourceId: string;
  sourceLocator: string;
  recordedAt: string;
};

const SHARE_CLASS_ISIN = /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;

export function citedShareClassHref(isin: string | null | undefined): string | null {
  const value = isin?.trim() ?? "";
  if (!SHARE_CLASS_ISIN.test(value)) return null;
  return `/explore?isin=${encodeURIComponent(value)}`;
}

export type PricePointView = {
  priceType: string;
  valueText: string;
  quoteUnit: string;
  currency: string;
  sessionDate: string;
  sourceId: string;
  adjustmentStatus: string;
  retrievedAt: string;
  delayClass: string;
  quality: string;
};

export type PriceFreshnessView = {
  close: PricePointView | null;
  nav: PricePointView | null;
  quote: PricePointView | null;
  closeCount: number;
  adjustedClose: PricePointView | null;
  adjustedCloseCount: number;
  adjustedFirstDate: string | null;
  adjustedLastDate: string | null;
  adjustedCurrency: string | null;
  reason: string;
};

export type ApprovalHistoryView = {
  decision: string;
  actor: string;
  rationale: string;
  recordedAt: string;
};

export type EligibilityDecisionView = {
  decision: string;
  conditions: string;
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
  exposures: CitedExposureView[];
  prices: PriceFreshnessView;
  approvals: ApprovalHistoryView[];
  eligibilityDecisions: EligibilityDecisionView[];
  fxSentence: string;
  overlapReason: string;
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
    return "No eligibility assessment is stored. Missing hard evidence stays unknown. There is no rank. Eligibility is not founder approval.";
  }
  return `${share.assessment.eligibility}. Evidence ${share.assessment.evidenceStatus}. ${share.assessment.statement} Eligibility is not founder approval.`;
}

export const PRICE_ABSENT =
  "No licensed close is stored. A missing price is not zero.";

export function absentPrices(reason = PRICE_ABSENT): PriceFreshnessView {
  return {
    close: null,
    nav: null,
    quote: null,
    closeCount: 0,
    adjustedClose: null,
    adjustedCloseCount: 0,
    adjustedFirstDate: null,
    adjustedLastDate: null,
    adjustedCurrency: null,
    reason,
  };
}

export const APPROVAL_ABSENT =
  "No founder approval is stored. Eligibility is a separate decision.";

export const FX_GAP =
  "No rights-cleared SGD reference rate is stored. Broker FX is a different series.";

export const OVERLAP_UNAVAILABLE =
  "Overlap is unavailable. Top-ten holdings stay partial, and missing holdings are not an empty portfolio.";

export const PERFORMANCE_SEPARATE =
  "Market-price return, NAV return, and total return stay separate. None is calculated on this page, and none is a recommendation.";

export function priceCopy(share: EtfShareExplore): string {
  const close = share.prices.close;
  if (!close) return share.prices.reason || PRICE_ABSENT;
  const stale = close.quality === "stale" ? " This close is stale." : "";
  return `Close ${close.valueText} ${close.quoteUnit} on ${close.sessionDate}. Adjustment ${close.adjustmentStatus}. Delay ${close.delayClass}. Source ${close.sourceId}. Retrieved ${close.retrievedAt}.${stale} Stored closes: ${share.prices.closeCount}.`;
}

export function adjustedCloseCopy(share: EtfShareExplore): string {
  const prices = share.prices;
  if (prices.adjustedCloseCount === 0) return "";
  const currency = prices.adjustedCurrency;
  const first = prices.adjustedFirstDate;
  const last = prices.adjustedLastDate;
  if (!currency || !first || !last) {
    return `The adjusted close count is ${prices.adjustedCloseCount}. Currency or dates are incomplete. This is not a raw close.`;
  }
  return `Adjusted close in ${currency} from ${first} to ${last}. The stored count is ${prices.adjustedCloseCount}. This is not a raw close.`;
}

export function navCopy(share: EtfShareExplore): string {
  const nav = share.prices.nav;
  if (!nav) return "No NAV is stored. NAV is not the listing close.";
  return `NAV ${nav.valueText} ${nav.quoteUnit} on ${nav.sessionDate}. Source ${nav.sourceId}.`;
}

export function quoteCopy(share: EtfShareExplore): string {
  const quote = share.prices.quote;
  if (!quote) return "No bid, ask, or last trade is stored. A quote is not the close.";
  return `${quote.priceType} ${quote.valueText} ${quote.quoteUnit}. Delay ${quote.delayClass}. Retrieved ${quote.retrievedAt}. Quality ${quote.quality}.`;
}

export function approvalCopy(share: EtfShareExplore): string {
  if (share.approvals.length === 0) return APPROVAL_ABSENT;
  return share.approvals
    .map((row) => `${row.decision} by ${row.actor} at ${row.recordedAt}. ${row.rationale}`)
    .join(" ");
}

export function eligibilityDecisionCopy(share: EtfShareExplore): string {
  if (share.eligibilityDecisions.length === 0) {
    return "No separate eligibility decision is stored. Missing evidence stays insufficient.";
  }
  return share.eligibilityDecisions
    .map((row) => `${row.decision}. ${row.conditions} Recorded ${row.recordedAt}.`)
    .join(" ");
}

export function freshnessCopy(share: EtfShareExplore): string {
  return `Share class row recorded ${share.recordedAt}. That timestamp is not a market-data as-of date.`;
}

export function exposureCopy(exposure: CitedExposureView): string {
  const weight = exposure.weightText ? `Weight ${exposure.weightText}.` : "No weight is cited.";
  return `${exposure.exposureClass}. ${weight} As of ${exposure.asOf}. Evidence cited. Source ${exposure.sourceId}. Locator ${exposure.sourceLocator}. Recorded ${exposure.recordedAt}.`;
}

export const EXPOSURES_ABSENT = "No cited exposure is stored.";

export const SHARE_CLASS_ABSENT = "No cited share class is stored for this ISIN.";
