/**
 * Human-readable register for the tracked conditions series.
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
  /** What a stored "thousands" level counts. Absent for rates, indexes and dollars. */
  countNoun?: "jobs" | "openings";
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
    countNoun: "jobs",
    measures:
      "The number of paid jobs on nonfarm payrolls in the United States, from the establishment survey. The Bureau publishes the level in thousands of jobs. Shown here in millions of jobs.",
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
    countNoun: "openings",
    measures:
      "The number of job openings on the last business day of the month for total nonfarm. The Bureau publishes the level in thousands of job openings. Shown here in millions of job openings.",
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
      "A change on the chart is a move in the index, in index points. The stored 12-month percent change is a separate reading. It uses the two endpoint index levels and is not the index level.",
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
      "The net percentage of domestic banks reporting tighter standards on commercial and industrial loans to large and middle-market firms, shown in percent. A positive figure means more banks tightened than eased. It is not a volume of credit.",
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
      "Bank credit at commercial banks in the United States. The Board publishes the level in millions of US dollars. Shown here in trillions of US dollars. A smaller change is shown in billions or millions. Observations are weekly.",
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
  {
    sourceId: "ecb_hicp_core",
    region: "Euro area",
    organisation: "European Central Bank",
    datasetLabel: "Harmonised index of consumer prices",
    sourceHref:
      "https://data-api.ecb.europa.eu/service/data/ICP/M.U2.Y.XEF000.3.INX?format=csvdata",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "index, 2015 = 100",
    measures:
      "The euro-area harmonised index of consumer prices excluding energy and food, working-day and seasonally adjusted, with 2015 = 100. The European Central Bank is the compiler. This panel shows the index level, not a year-on-year rate.",
    matters:
      "It leaves out energy and food, which often move for reasons other than domestic demand. It is still a price index, not a forecast of returns.",
  },
  {
    sourceId: "ecb_fm_deposit_facility",
    region: "Euro area",
    organisation: "European Central Bank",
    datasetLabel: "Key ECB interest rates",
    sourceHref:
      "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "percent_per_year",
    measures:
      "The euro-area deposit facility rate, the rate banks receive on overnight deposits at the Eurosystem, in percent per year. The file is a daily level provided by the ECB. Seasonal adjustment is not stated.",
    matters:
      "It is a policy rate. A change is a change in that administered rate, not a market forecast and not a sovereign yield.",
  },
  {
    sourceId: "eurostat_unemployment_ea21",
    region: "Euro area",
    organisation: "Eurostat",
    datasetLabel: "Unemployment by sex and age",
    sourceHref:
      "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_m?lang=EN&age=TOTAL&geo=EA21&s_adj=SA&sex=T&unit=PC_ACT",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "percent",
    measures:
      "The euro-area unemployment rate for EA21, Eurostat's euro area of 21 countries from 2026, seasonally adjusted and not calendar adjusted. It is the percentage of the population in the labour force. It is not the EU27 rate.",
    matters:
      "A rise can indicate weaker demand for labour in the euro area. It does not count people who have left the labour force, and it is not the United States rate.",
  },
  {
    sourceId: "eurostat_gdp_real_ea21",
    region: "Euro area",
    organisation: "Eurostat",
    datasetLabel: "Gross domestic product and main components",
    sourceHref:
      "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/namq_10_gdp?lang=EN&geo=EA21&na_item=B1GQ&s_adj=SCA&unit=CLV_I15",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "index, 2015 = 100",
    measures:
      "Euro-area real gross domestic product for EA21, chain-linked volumes, index 2015 = 100, seasonally and calendar adjusted. Geography is the euro area of 21 countries from 2026, not the EU27.",
    matters:
      "The index level shows the volume of output. A change is a move in that index, not a judgement about the investment environment.",
  },
  {
    sourceId: "eurostat_industrial_production_ea21",
    region: "Euro area",
    organisation: "Eurostat",
    datasetLabel: "Production in industry",
    sourceHref:
      "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sts_inpr_m?lang=EN&geo=EA21&indic_bt=PRD&nace_r2=B-D&s_adj=SCA&unit=I21",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "index, 2021 = 100",
    measures:
      "Euro-area industrial production for EA21, industry groups B to D, seasonally and calendar adjusted, index 2021 = 100. It is a volume index, not the EU27 series.",
    matters:
      "It records production in mining, manufacturing and energy supply. A change is a move in the index, not a forecast of company earnings.",
  },
  {
    sourceId: "eurostat_retail_volume_ea21",
    region: "Euro area",
    organisation: "Eurostat",
    datasetLabel: "Retail trade volume",
    sourceHref:
      "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sts_trtu_m?lang=EN&geo=EA21&indic_bt=VOL_SLS&nace_r2=G47&s_adj=SCA&unit=I21",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "index, 2021 = 100",
    measures:
      "Euro-area retail sales volume for EA21, excluding motor vehicles, seasonally and calendar adjusted, index 2021 = 100. Net turnover from the same table is not shown. It is not the EU27 series.",
    matters:
      "Volume of sales is a quantity measure. It can move when households buy more or less. It is not a price index and not a forecast of retail profits.",
  },
  {
    sourceId: "stat_cpi_2025_all_items_reference",
    region: "Japan",
    organisation: "Statistics Bureau of Japan",
    datasetLabel: "Three-decimal reference index",
    sourceHref: "https://www.stat.go.jp/data/cpi/1.html",
    linkKind: "publication",
    retrievalHref: "https://www.stat.go.jp/data/cpi/2025/csv/zmi2025aa.csv",
    expectedUnit:
      "index, 2025 = 100, three-decimal reference price index, not a nominal yen amount and not a real volume",
    measures:
      "The Japanese all-items consumer price reference index, published to three decimal places, with 2025 = 100. It is not the official one-decimal consumer price index. Periods are calendar months and the series is not seasonally adjusted.",
    matters:
      "A change is a move in the reference index, in index points. It is not a year-on-year inflation rate and it is not the official one-decimal index.",
  },
  {
    sourceId: "cao_mo_private_ex_volatile_sa_monthly",
    region: "Japan",
    organisation: "Cabinet Office, Economic and Social Research Institute",
    datasetLabel: "Machinery orders",
    sourceHref: "https://www.esri.cao.go.jp/jp/stat/juchu/juchu.html",
    linkKind: "publication",
    retrievalHref: "https://www.esri.cao.go.jp/jp/stat/juchu/2026/2608chouki-1.xlsx",
    expectedUnit: "million yen, nominal, not a real volume index",
    measures:
      "Private machinery orders in Japan, excluding ships and electric power, in nominal million yen. The series is seasonally adjusted and monthly. It is not a real volume index and it is not a fiscal-year total.",
    matters:
      "Orders can move before production. A change is a change in the nominal amount, not a forecast of company earnings.",
  },
  {
    sourceId: "bis_gli_usd_credit_nonbanks",
    region: "Global",
    organisation: "Bank for International Settlements",
    datasetLabel: "Global liquidity indicators",
    sourceHref:
      "https://stats.bis.org/api/v1/data/WS_GLI/Q.USD.3P.N.A.I.B.USD/all?detail=full",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "US dollar, millions",
    measures:
      "US dollar credit to non-bank borrowers outside the United States, in millions of US dollars. The series covers bank loans and debt securities and is quarterly. The Bank for International Settlements publishes the current file.",
    matters:
      "A rise means more dollar credit is outstanding to those borrowers. It is a credit stock. It is not a United States domestic bank-credit series and it is not a forecast of returns.",
  },
  {
    sourceId: "ons_mm23_cpi_d7bt",
    region: "United Kingdom",
    organisation: "Office for National Statistics",
    datasetLabel: "CPI all items",
    sourceHref:
      "https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/d7bt/mm23",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "index, 2015 = 100",
    measures:
      "The consumer price index for all items, geography GB, with 2015 = 100. It is not seasonally adjusted. This panel shows the index level, not a year-on-year inflation rate.",
    matters:
      "A change is a move in the price index, in index points. It is the Office for National Statistics all-items index, not the euro-area harmonised index.",
  },
  {
    sourceId: "boe_official_bank_rate",
    region: "United Kingdom",
    organisation: "Bank of England",
    datasetLabel: "Official Bank Rate",
    sourceHref:
      "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/1975&Dateto=now&SeriesCodes=IUDBEDR&CSVF=CT&UsingCodes=Y",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "percent",
    measures:
      "The Bank of England Bank Rate, in percent. It is the official policy rate for the United Kingdom. It is not an exchange rate and it is not a market yield.",
    matters:
      "A change is a change in that administered rate. It does not measure the pound's exchange rate and it is not a forecast of returns.",
  },
  {
    sourceId: "dosm_ipi_abs",
    region: "Malaysia",
    organisation: "Department of Statistics Malaysia",
    datasetLabel: "Industrial production index",
    sourceHref: "https://storage.dosm.gov.my/ipi/ipi.csv",
    linkKind: "series",
    retrievalHref: null,
    expectedUnit: "index, 2015 = 100",
    measures:
      "The Malaysian industrial production index, absolute level, with 2015 = 100. It is not seasonally adjusted. Growth rates in the same file are not shown.",
    matters:
      "It records the volume of industrial production in Malaysia. A change is a move in the index, not a forecast of company earnings.",
  },
];

const BY_ID = new Map(INDICATOR_METADATA.map((item) => [item.sourceId, item]));

export function indicatorMetadata(sourceId: string): IndicatorMetadata | undefined {
  return BY_ID.get(sourceId);
}

export const SERIES_PAGE_UNAVAILABLE =
  "A separate series page is not in the verified source register.";
