/** Latest stored observations drawn for one series. Earlier history is not loaded. */
export const MACRO_CONDITIONS_WINDOW = 12;

/** A monthly series is stale when its latest period starts before this many months ago. */
export const MONTHLY_STALE_MONTHS = 2;

/** A weekly series is stale when its latest period starts more than this many days ago. */
export const WEEKLY_STALE_DAYS = 21;

/** A quarterly series is stale when its latest period starts before this many quarters ago. */
export const QUARTERLY_STALE_QUARTERS = 2;

/** A daily series is stale when its latest period starts more than this many days ago. */
export const DAILY_STALE_DAYS = 5;

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
 * Live indicator series refreshed by workers/research.
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
    name: "Discontinued euro-area HICP",
  },
  {
    sourceId: "ecb_hicp_core",
    groupId: "inflation",
    groupLabel: "Inflation",
    name: "Discontinued euro-area core HICP",
  },
  {
    sourceId: "eurostat_hicp_total_ea",
    groupId: "inflation",
    groupLabel: "Inflation",
    name: "Euro area all-items HICP",
  },
  {
    sourceId: "ecb_fm_deposit_facility",
    groupId: "rates",
    groupLabel: "Rates",
    name: "Deposit facility rate",
  },
  {
    sourceId: "eurostat_unemployment_ea21",
    groupId: "labour",
    groupLabel: "Labour",
    name: "Euro area unemployment rate",
  },
  {
    sourceId: "eurostat_gdp_real_ea21",
    groupId: "growth",
    groupLabel: "Growth",
    name: "Euro area real GDP",
  },
  {
    sourceId: "eurostat_industrial_production_ea21",
    groupId: "manufacturing",
    groupLabel: "Manufacturing",
    name: "Euro area industrial production",
  },
  {
    sourceId: "eurostat_retail_volume_ea21",
    groupId: "trade",
    groupLabel: "Trade",
    name: "Euro area retail sales volume",
  },
  {
    sourceId: "stat_cpi_2025_all_items_reference",
    groupId: "inflation",
    groupLabel: "Inflation",
    name: "CPI reference index",
  },
  {
    sourceId: "cao_mo_private_ex_volatile_sa_monthly",
    groupId: "manufacturing",
    groupLabel: "Manufacturing",
    name: "Machinery orders",
  },
  {
    sourceId: "bis_gli_usd_credit_nonbanks",
    groupId: "credit",
    groupLabel: "Credit",
    name: "US dollar credit to non-banks",
  },
  {
    sourceId: "ons_mm23_cpi_d7bt",
    groupId: "inflation",
    groupLabel: "Inflation",
    name: "UK CPI all items",
  },
  {
    sourceId: "boe_official_bank_rate",
    groupId: "rates",
    groupLabel: "Rates",
    name: "Bank Rate",
  },
  {
    sourceId: "dosm_ipi_abs",
    groupId: "manufacturing",
    groupLabel: "Manufacturing",
    name: "Malaysia industrial production",
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
