/** Latest stored observations drawn for one series. Earlier history is not loaded. */
export const MACRO_CONDITIONS_WINDOW = 12;

/** A monthly series is stale when its latest period starts before this many months ago. */
export const MONTHLY_STALE_MONTHS = 2;

/** A weekly series is stale when its latest period starts more than this many days ago. */
export const WEEKLY_STALE_DAYS = 21;

/** A quarterly series is stale when its latest period starts before this many quarters ago. */
export const QUARTERLY_STALE_QUARTERS = 2;

export type StoredObservation = {
  period: string;
  rawValue: string;
};

export type StoredSeriesWindow = {
  sourceId: string;
  datasetId: string;
  retrievedAt: string | null;
  seriesProvenance: string | null;
  unit: string;
  seasonalAdjustment: string;
  frequency: string;
  observations: StoredObservation[];
};

export type MacroSeriesSpec = {
  sourceId: string;
  groupId: string;
  groupLabel: string;
  name: string;
};

/**
 * The ten live indicator series refreshed by workers/research.
 * Monetary-policy press is a publication record, not a rates series.
 */
export const MACRO_SERIES: readonly MacroSeriesSpec[] = [
  {
    sourceId: "bls_cps_unemployment_rate",
    groupId: "labour",
    groupLabel: "Labour",
    name: "Unemployment rate",
  },
  {
    sourceId: "bls_ces_total_nonfarm_payrolls",
    groupId: "labour",
    groupLabel: "Labour",
    name: "Total nonfarm payrolls",
  },
  {
    sourceId: "bls_jolts_total_nonfarm_job_openings",
    groupId: "labour",
    groupLabel: "Labour",
    name: "Job openings",
  },
  {
    sourceId: "bls_cpi_u_all_items",
    groupId: "inflation",
    groupLabel: "Inflation",
    name: "CPI-U all items",
  },
  {
    sourceId: "federal_reserve_g17_total_ip",
    groupId: "growth",
    groupLabel: "Growth",
    name: "Industrial production",
  },
  {
    sourceId: "federal_reserve_sloos_cil",
    groupId: "credit",
    groupLabel: "Credit",
    name: "Business credit standards",
  },
  {
    sourceId: "federal_reserve_h8_bank_credit",
    groupId: "credit",
    groupLabel: "Credit",
    name: "Bank credit",
  },
  {
    sourceId: "federal_reserve_h15_federal_funds_effective",
    groupId: "rates",
    groupLabel: "Rates",
    name: "Federal funds rate",
  },
  {
    sourceId: "federal_reserve_h15_treasury_10y_constant_maturity",
    groupId: "rates",
    groupLabel: "Rates",
    name: "10-year yield",
  },
  {
    sourceId: "ecb_sdw_hicp_sa",
    groupId: "international",
    groupLabel: "International",
    name: "Euro area HICP",
  },
];

export const UNAVAILABLE_CONDITIONS = [
  {
    id: "liquidity",
    name: "Liquidity",
    detail: "Liquidity is not available. No live series is tracked for it.",
  },
  {
    id: "monetary_policy_stance",
    name: "Monetary-policy stance",
    detail:
      "Monetary-policy stance is not available. No live series is tracked for it. Monetary-policy press is a publication record, not a rates panel.",
  },
] as const;

export const EXCLUDED_PRESS_SOURCE_IDS = [
  "federal_reserve_monetary_press",
  "ecb_monetary_press",
] as const;
