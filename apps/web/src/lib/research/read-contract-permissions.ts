/**
 * Version 2 of the research read contract.
 *
 * What a later intelligence consumer may use. This is not an engine and it
 * does not combine the methods into a narrative. publication_allowed stays false.
 */

import type { ResearchConsumerUse } from "./read-contract-types.ts";

export type MethodPermission = {
  methodId: string;
  purpose: string;
  consumerUse: ResearchConsumerUse;
  publicationAllowed: false;
};

export const METHOD_PERMISSIONS: readonly MethodPermission[] = [
  { methodId: "BRY_BOSCHAN_SPENCER15_VARIANT", purpose: "Retrospective turning points on industrial production", consumerUse: "retrospective_diagnostic", publicationAllowed: false },
  { methodId: "HARDING_PAGAN_CHARACTERISTICS", purpose: "Phase and concordance from stored turning points", consumerUse: "retrospective_diagnostic", publicationAllowed: false },
  { methodId: "BAI_PERRON_MEAN_SHIFTS", purpose: "Mean-shift dates under a predeclared trim", consumerUse: "retrospective_diagnostic", publicationAllowed: false },
  { methodId: "CUSUM_RECURSIVE_RESIDUALS", purpose: "Stability of a stated industrial-production regression", consumerUse: "retrospective_diagnostic", publicationAllowed: false },
  { methodId: "IP_GROWTH_CUSUM", purpose: "Stability of industrial-production growth", consumerUse: "retrospective_diagnostic", publicationAllowed: false },
  { methodId: "ENGLE_GRANGER_COINTEGRATION", purpose: "Cointegration diagnostic on latest revised log levels", consumerUse: "retrospective_diagnostic", publicationAllowed: false },
  { methodId: "AUTOREGRESSIVE_BENCHMARK", purpose: "Benchmark against the historical mean", consumerUse: "retrospective_diagnostic", publicationAllowed: false },
  { methodId: "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT", purpose: "Coincident factor from the accepted parameter version", consumerUse: "retrospective_diagnostic", publicationAllowed: false },
  { methodId: "ESTRELLA_MISHKIN_TERM_SPREAD", purpose: "Latest revised 10-year minus 3-month yield spread", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "EX_POST_REAL_FEDERAL_FUNDS_RATE", purpose: "Funds rate minus trailing CPI inflation", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "EX_POST_REAL_FUNDS_RATE", purpose: "Funds rate minus subsequent CPI inflation", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "CPI_U_INFLATION_AUTREGRESSION", purpose: "Persistence of monthly CPI-U log changes", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "LEAD_LAG_CROSS_CORRELATION", purpose: "Cross-correlation of the four coincident growth rates", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "LABOUR_MARKET_CONDITIONS", purpose: "Stored labour-market family reading", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "PRICES_AND_POLICY", purpose: "Stored prices and policy family reading", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "INDUSTRIAL_PRODUCTION_ACTIVITY", purpose: "Stored industrial-production family reading", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "CREDIT_STANDARDS_AND_VOLUMES", purpose: "Stored credit family reading", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "SLOOS_CIL_LENDING_STANDARDS", purpose: "SLOOS commercial and industrial standards", consumerUse: "descriptive_measurement", publicationAllowed: false },
  { methodId: "CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT", purpose: "Predeclared constant-maturity spread probability", consumerUse: "probability_estimate", publicationAllowed: false },
  { methodId: "HAMILTON_MONTHLY_REGIME_SWITCHING", purpose: "Experimental monthly regime probabilities", consumerUse: "experimental_only", publicationAllowed: false },
  { methodId: "RESTRICTED_COINCIDENT_DIFFUSION", purpose: "Experimental four-series diffusion share", consumerUse: "experimental_only", publicationAllowed: false },
  { methodId: "SAHM_UNEMPLOYMENT_GAP", purpose: "Sahm gap on the latest unemployment window", consumerUse: "blocked", publicationAllowed: false },
  { methodId: "INFLATION_AUTOREGRESSION", purpose: "Holdout inflation autoregression", consumerUse: "blocked", publicationAllowed: false },
  { methodId: "CENSUS_ADV_DURABLE_ORDERS", purpose: "Census advance durable goods orders", consumerUse: "blocked", publicationAllowed: false },
  { methodId: "MACRO_CONDITIONS_PANEL", purpose: "Macro conditions panel including Census orders", consumerUse: "blocked", publicationAllowed: false },
  { methodId: "PERIOD_LEVEL_CHANGE", purpose: "Period change in the unemployment rate", consumerUse: "blocked", publicationAllowed: false },
];

export function permissionFor(methodId: string): MethodPermission | null {
  return METHOD_PERMISSIONS.find((row) => row.methodId === methodId) ?? null;
}
