/**
 * Human-readable register for the ten tracked conditions series.
 * Links are copied from docs/sources/SOURCE_RIGHTS.csv. The metadata test
 * refuses a URL that is not in that row's access or evidence fields.
 */

export type IndicatorLinkKind = "series" | "publication" | "data_file";

export type IndicatorMetadata = {
  sourceId: string;
  region: string;
  organisation: string;
  datasetLabel: string;
  /** Verified URL a reader can open. */
  sourceHref: string;
  linkKind: IndicatorLinkKind;
  /** Second verified URL when the public link is not the retrieval file. */
  retrievalHref: string | null;
  expectedUnit: string;
  measures: string;
  matters: string;
};

export const INDICATOR_METADATA: readonly IndicatorMetadata[] = [
  {
    sourceId: "bls_cps_unemployment_rate",
    region: "United States",
    organisation: "U.S. Bureau of Labor Statistics",
    datasetLabel: "Current Population Survey",
    sourceHref: "https://data.bls.gov/timeseries/LNS14000000",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "percent",
    measures:
      "The share of the civilian labour force that is unemployed and actively looking for work, from the Current Population Survey. Shown in percent.",
    matters:
      "A rise can indicate weaker demand for labour. It should be read with payrolls, vacancies and other indicators, and it does not count people who have left the labour force.",
  },
  {
    sourceId: "bls_ces_total_nonfarm_payrolls",
    region: "United States",
    organisation: "U.S. Bureau of Labor Statistics",
    datasetLabel: "Current Employment Statistics",
    sourceHref: "https://download.bls.gov/pub/time.series/ce/ce.data.00a.TotalNonfarm.Employment",
    linkKind: "data_file",
    retrievalHref: null,
    expectedUnit: "thousands",
    measures:
      "The number of paid jobs on nonfarm payrolls in the United States, from the establishment survey. The Bureau publishes the level in thousands of jobs. Shown here in people.",
    matters:
      "The month-to-month change shows whether employers added or cut jobs. One person can hold more than one job, so this is a count of jobs rather than of people in the labour force.",
  },
  {
    sourceId: "bls_jolts_total_nonfarm_job_openings",
    region: "United States",
    organisation: "U.S. Bureau of Labor Statistics",
    datasetLabel: "Job Openings and Labour Turnover Survey",
    sourceHref: "https://download.bls.gov/pub/time.series/jt/jt.data.2.JobOpenings",
    linkKind: "data_file",
    retrievalHref: null,
    expectedUnit: "thousands",
    measures:
      "The number of job openings on the last business day of the month for total nonfarm. The Bureau publishes the level in thousands. Shown here in people.",
    matters:
      "Openings record vacancies employers are seeking to fill. They can fall after roles are filled or after vacancies are withdrawn. They are not the unemployment rate.",
  },
  {
    sourceId: "bls_cpi_u_all_items",
    region: "United States",
    organisation: "U.S. Bureau of Labor Statistics",
    datasetLabel: "Consumer Price Index for All Urban Consumers",
    sourceHref: "https://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems",
    linkKind: "data_file",
    retrievalHref: null,
    expectedUnit: "1982-84=100",
    measures:
      "The Consumer Price Index for All Urban Consumers, all items, as a price index with 1982–84 = 100. It follows a fixed basket for urban consumers. This panel shows the index level, not a 12-month inflation rate.",
    matters:
      "A change is a move in the index, in index points. An inflation rate would need both endpoint months and a defined comparison. That rate is not calculated here.",
  },
  {
    sourceId: "federal_reserve_g17_total_ip",
    region: "United States",
    organisation: "Board of Governors of the Federal Reserve System",
    datasetLabel: "Industrial Production and Capacity Utilization (G.17)",
    sourceHref: "https://www.federalreserve.gov/releases/g17/",
    linkKind: "publication",
    retrievalHref:
      "https://www.federalreserve.gov/datadownload/Output.aspx?rel=G17&series=5d88c03b0036f0334d78f6bafefc5101&lastobs=&from=&to=&filetype=csv&label=include&layout=seriesrow&type=package",
    expectedUnit: "index_2017_100",
    measures:
      "The Federal Reserve index of real output in manufacturing, mining and utilities, total index, with 2017 = 100. This is an output index, not a price index and not a growth rate.",
    matters:
      "A movement shows the direction of industrial output over the comparison period. It does not by itself describe demand in the rest of the economy.",
  },
  {
    sourceId: "federal_reserve_sloos_cil",
    region: "United States",
    organisation: "Board of Governors of the Federal Reserve System",
    datasetLabel: "Senior Loan Officer Opinion Survey",
    sourceHref: "https://www.federalreserve.gov/data/sloos/sloos.htm",
    linkKind: "publication",
    retrievalHref: "https://www.federalreserve.gov/datadownload/Output.aspx?rel=SLOOS&filetype=zip",
    expectedUnit: "percent_net_tightening",
    measures:
      "The net percentage of domestic banks reporting tighter standards on commercial and industrial loans to large and middle-market firms. A positive figure means more banks tightened than eased. It is not a volume of credit.",
    matters:
      "It records how loan officers describe the change in standards over the survey quarter. It is not the stock of bank credit and it is not a forecast of defaults.",
  },
  {
    sourceId: "federal_reserve_h8_bank_credit",
    region: "United States",
    organisation: "Board of Governors of the Federal Reserve System",
    datasetLabel: "Assets and Liabilities of Commercial Banks (H.8)",
    sourceHref: "https://www.federalreserve.gov/releases/h8/current/default.htm",
    linkKind: "publication",
    retrievalHref: "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H8&filetype=zip",
    expectedUnit: "usd_millions",
    measures:
      "Bank credit at commercial banks in the United States. The Board publishes the level in millions of US dollars. Shown here in dollars. Observations are weekly.",
    matters:
      "The change shows whether the stock of bank credit grew or shrank over the comparison week. It covers loans and securities on bank balance sheets, not lending standards.",
  },
  {
    sourceId: "federal_reserve_h15_federal_funds_effective",
    region: "United States",
    organisation: "Board of Governors of the Federal Reserve System",
    datasetLabel: "Selected Interest Rates (H.15)",
    sourceHref: "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&filetype=zip",
    linkKind: "data_file",
    retrievalHref: null,
    expectedUnit: "percent_per_year",
    measures:
      "The monthly effective federal funds rate: the volume-weighted median of overnight federal funds transactions, in percent per year.",
    matters:
      "It is the observed overnight rate in the federal funds market, close to the Federal Open Market Committee target range. It is the price of those overnight balances, not a forecast of asset returns.",
  },
  {
    sourceId: "federal_reserve_h15_treasury_10y_constant_maturity",
    region: "United States",
    organisation: "Board of Governors of the Federal Reserve System",
    datasetLabel: "Selected Interest Rates (H.15)",
    sourceHref: "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&filetype=zip",
    linkKind: "data_file",
    retrievalHref: null,
    expectedUnit: "percent_per_year",
    measures:
      "The monthly market yield on United States Treasury securities at 10-year constant maturity, quoted on an investment basis, in percent per year.",
    matters:
      "It is a long-term nominal government yield. It can move with expected inflation, expected short-term rates and the extra yield investors require for a longer maturity. It is not a forecast of equity returns.",
  },
  {
    sourceId: "ecb_sdw_hicp_sa",
    region: "Euro area",
    organisation: "European Central Bank",
    datasetLabel: "Harmonised Index of Consumer Prices",
    sourceHref:
      "https://data-api.ecb.europa.eu/service/data/ICP/M.U2.Y.000000.3.INX?format=csvdata",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "index, 2015 = 100",
    measures:
      "The euro-area Harmonised Index of Consumer Prices, all items, working-day and seasonally adjusted, with 2015 = 100. This panel shows the index level, not a year-on-year inflation rate.",
    matters:
      "A change is a move in the price index, in index points. When the latest month is old, the figure does not describe current euro-area prices.",
  },
];

const BY_ID = new Map(INDICATOR_METADATA.map((item) => [item.sourceId, item]));

export function indicatorMetadata(sourceId: string): IndicatorMetadata | undefined {
  return BY_ID.get(sourceId);
}

export const SERIES_PAGE_UNAVAILABLE =
  "A separate series page is not in the verified source register.";
