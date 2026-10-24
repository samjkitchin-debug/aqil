import { indicatorMetadata } from "../research/indicator-metadata.ts";
import { MACRO_SERIES } from "../research/macro-conditions.ts";
import { NOT_INVESTMENT_CONCLUSION } from "../research/present-economic-evidence.ts";
import { STORED_US_READING_HEADING } from "../research/present-macro-conditions.ts";

const US_ACTIVITY = [
  "bls_cps_unemployment_rate",
  "bls_ces_total_nonfarm_payrolls",
  "bls_jolts_total_nonfarm_job_openings",
  "bls_cpi_u_all_items",
  "federal_reserve_g17_total_ip",
  "federal_reserve_h8_bank_credit",
  "federal_reserve_sloos_cil",
  "federal_reserve_h15_federal_funds_effective",
  "federal_reserve_h15_treasury_10y_constant_maturity",
] as const;

const EURO_ACTIVITY = [
  "eurostat_gdp_real_ea21",
  "eurostat_unemployment_ea21",
  "eurostat_industrial_production_ea21",
  "eurostat_retail_volume_ea21",
  "ecb_fm_deposit_facility",
] as const;

const UK_PRICES_AND_RATE = ["ons_mm23_cpi_d7bt", "boe_official_bank_rate"] as const;

const JAPAN = ["stat_cpi_2025_all_items_reference", "cao_mo_private_ex_volatile_sa_monthly"] as const;

const MALAYSIA = ["dosm_ipi_abs"] as const;

const BIS_CREDIT = ["bis_gli_usd_credit_nonbanks"] as const;

const HICP = ["eurostat_hicp_total_ea", "ecb_sdw_hicp_sa", "ecb_hicp_core"] as const;

const POLICY_RATES = [
  "federal_reserve_h15_federal_funds_effective",
  "federal_reserve_h15_treasury_10y_constant_maturity",
  "ecb_fm_deposit_facility",
  "boe_official_bank_rate",
] as const;

const DEVELOPED = [...US_ACTIVITY, ...EURO_ACTIVITY, ...UK_PRICES_AND_RATE, ...JAPAN] as const;

const BROAD_GLOBAL = [...DEVELOPED, ...MALAYSIA, ...BIS_CREDIT] as const;

const CONTEXT_SENTENCE = "These series are stored context for this exposure class.";

const MISSING_CLASS = "No operational series is stored for this exposure class.";

type ReadingHref = "/conditions?region=united-states" | "/conditions?region=global";

type FamilyMap = {
  series: readonly string[];
  unitedStatesReading: ReadingHref | null;
};

const FAMILIES: Record<string, FamilyMap | "sector" | "factor"> = {
  "Broad global equity": { series: BROAD_GLOBAL, unitedStatesReading: "/conditions?region=global" },
  "Global developed equity": { series: DEVELOPED, unitedStatesReading: "/conditions?region=global" },
  "Emerging equity": { series: MALAYSIA, unitedStatesReading: null },
  "US equity": { series: US_ACTIVITY, unitedStatesReading: "/conditions?region=united-states" },
  "Europe equity": {
    series: [...EURO_ACTIVITY, ...UK_PRICES_AND_RATE, ...HICP],
    unitedStatesReading: null,
  },
  "Asia-Pacific developed equity": { series: JAPAN, unitedStatesReading: null },
  "Asia-Pacific emerging equity": { series: MALAYSIA, unitedStatesReading: null },
  "Investment-grade bond": {
    series: [...POLICY_RATES, ...BIS_CREDIT],
    unitedStatesReading: null,
  },
  "Government bond": { series: POLICY_RATES, unitedStatesReading: null },
  "Inflation-linked bond": {
    series: [
      "bls_cpi_u_all_items",
      "ons_mm23_cpi_d7bt",
      "stat_cpi_2025_all_items_reference",
      ...HICP,
    ],
    unitedStatesReading: null,
  },
  "Broad technology, healthcare, or financials sector equity": "sector",
  "Quality, value, or minimum-volatility factor equity": "factor",
};

export type MappedSeries = {
  sourceId: string;
  name: string;
  href: string;
};

export type ExposureContext =
  | { status: "missing"; sentence: string }
  | {
      status: "mapped";
      series: MappedSeries[];
      contextSentence: string;
      unitedStatesReading: { href: ReadingHref; heading: string; sentence: string } | null;
    };

function intelligenceRegion(sourceId: string): string {
  const region = indicatorMetadata(sourceId)?.region ?? "";
  if (region === "United States") return "united-states";
  if (region === "Euro area" || region === "United Kingdom") return "europe";
  if (region === "Japan") return "japan";
  if (region === "Malaysia") return "other-asia";
  return "global";
}

function seriesLink(sourceId: string): MappedSeries | null {
  const spec = MACRO_SERIES.find((item) => item.sourceId === sourceId);
  if (!spec) return null;
  const region = intelligenceRegion(sourceId);
  return {
    sourceId,
    name: spec.name,
    href: `/conditions?region=${region}#macro-panel-${sourceId}`,
  };
}

export function mapCitedExposure(exposureClass: string): ExposureContext {
  const family = FAMILIES[exposureClass];
  if (family === "sector") return { status: "missing", sentence: "No sector series is stored." };
  if (family === "factor") return { status: "missing", sentence: "No factor series is stored." };
  if (!family) return { status: "missing", sentence: MISSING_CLASS };
  const series = family.series.flatMap((sourceId) => {
    const link = seriesLink(sourceId);
    return link ? [link] : [];
  });
  if (series.length === 0) return { status: "missing", sentence: MISSING_CLASS };
  return {
    status: "mapped",
    series,
    contextSentence: CONTEXT_SENTENCE,
    unitedStatesReading: family.unitedStatesReading
      ? {
          href: family.unitedStatesReading,
          heading: STORED_US_READING_HEADING,
          sentence: NOT_INVESTMENT_CONCLUSION,
        }
      : null,
  };
}
