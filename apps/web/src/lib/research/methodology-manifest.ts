/**
 * One binding from a method id to its catalogue card, empty-state class, and presenter.
 * Planned cards have no method id and are not rows here.
 */

export type MethodologyEmptyState = "no-stored-run" | "stored-result-unavailable";

export type MethodologyBinding = {
  methodId: string;
  catalogueSlug: string;
  emptyState: MethodologyEmptyState;
  /** Key in the methodology presenter record. Null when this id has no presenter. */
  presenterKey: string | null;
};

export const METHODOLOGY_BINDINGS: readonly MethodologyBinding[] = [
  { methodId: "BRY_BOSCHAN_SPENCER15_VARIANT", catalogueSlug: "bry-boschan-spencer15", emptyState: "no-stored-run", presenterKey: "BRY_BOSCHAN_SPENCER15_VARIANT" },
  { methodId: "STOCK_WATSON_COINCIDENT_1988", catalogueSlug: "stock-watson-1988", emptyState: "no-stored-run", presenterKey: null },
  { methodId: "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT", catalogueSlug: "stock-watson-1988", emptyState: "no-stored-run", presenterKey: "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT" },
  { methodId: "RESTRICTED_COINCIDENT_DIFFUSION", catalogueSlug: "diffusion-index", emptyState: "no-stored-run", presenterKey: "RESTRICTED_COINCIDENT_DIFFUSION" },
  { methodId: "HARDING_PAGAN_CHARACTERISTICS", catalogueSlug: "harding-pagan-characteristics", emptyState: "no-stored-run", presenterKey: "HARDING_PAGAN_CHARACTERISTICS" },
  { methodId: "AUTOREGRESSIVE_BENCHMARK", catalogueSlug: "autoregressive-benchmark", emptyState: "no-stored-run", presenterKey: "AUTOREGRESSIVE_BENCHMARK" },
  { methodId: "LEAD_LAG_CROSS_CORRELATION", catalogueSlug: "lead-lag", emptyState: "no-stored-run", presenterKey: "LEAD_LAG_CROSS_CORRELATION" },
  { methodId: "SAHM_UNEMPLOYMENT_GAP", catalogueSlug: "sahm-rule", emptyState: "no-stored-run", presenterKey: "SAHM_UNEMPLOYMENT_GAP" },
  { methodId: "HAMILTON_MONTHLY_REGIME_SWITCHING", catalogueSlug: "hamilton-markov-switching", emptyState: "no-stored-run", presenterKey: "HAMILTON_MONTHLY_REGIME_SWITCHING" },
  { methodId: "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT", catalogueSlug: "yield-curve-probit", emptyState: "stored-result-unavailable", presenterKey: "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT" },
  { methodId: "BAI_PERRON_MEAN_SHIFTS", catalogueSlug: "bai-perron-breaks", emptyState: "no-stored-run", presenterKey: "BAI_PERRON_MEAN_SHIFTS" },
  { methodId: "CPI_U_INFLATION_AUTREGRESSION", catalogueSlug: "cpi-u-inflation-autoregression", emptyState: "stored-result-unavailable", presenterKey: "CPI_U_INFLATION_AUTREGRESSION" },
  { methodId: "EX_POST_REAL_FEDERAL_FUNDS_RATE", catalogueSlug: "ex-post-real-federal-funds-rate", emptyState: "stored-result-unavailable", presenterKey: "EX_POST_REAL_FEDERAL_FUNDS_RATE" },
  { methodId: "ENGLE_GRANGER_COINTEGRATION", catalogueSlug: "engle-granger-cointegration", emptyState: "stored-result-unavailable", presenterKey: "ENGLE_GRANGER_COINTEGRATION" },
  { methodId: "CUSUM_RECURSIVE_RESIDUALS", catalogueSlug: "cusum-recursive-residuals", emptyState: "stored-result-unavailable", presenterKey: "CUSUM_RECURSIVE_RESIDUALS" },
  { methodId: "INFLATION_AUTOREGRESSION", catalogueSlug: "inflation-autoregression", emptyState: "stored-result-unavailable", presenterKey: "INFLATION_AUTOREGRESSION" },
  { methodId: "EX_POST_REAL_FUNDS_RATE", catalogueSlug: "ex-post-real-funds-rate", emptyState: "stored-result-unavailable", presenterKey: "EX_POST_REAL_FUNDS_RATE" },
  { methodId: "IP_GROWTH_CUSUM", catalogueSlug: "ip-growth-cusum", emptyState: "stored-result-unavailable", presenterKey: "IP_GROWTH_CUSUM" },
  { methodId: "ESTRELLA_MISHKIN_TERM_SPREAD", catalogueSlug: "estrella-mishkin-spread", emptyState: "stored-result-unavailable", presenterKey: "ESTRELLA_MISHKIN_TERM_SPREAD" },
];

export function storedResultMethodIds(): ReadonlySet<string> {
  return new Set(
    METHODOLOGY_BINDINGS.filter((row) => row.emptyState === "stored-result-unavailable").map((row) => row.methodId),
  );
}

export function bindingForMethod(methodId: string): MethodologyBinding | undefined {
  return METHODOLOGY_BINDINGS.find((row) => row.methodId === methodId);
}
