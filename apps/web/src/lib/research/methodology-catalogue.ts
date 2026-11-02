/**
 * User-facing methodology register.
 *
 * Descriptions are the research question. They are not calculated results.
 * Live numbers must come from a stored research run, read on the server for a
 * signed-in reader. publication_allowed remains the publication gate and is
 * not set true to force display. This module does not read dossiers, CSV
 * registers, or calculation JSON.
 *
 * Promoting a planned card later is a research-system change plus a catalogue
 * edit: set stage to in-development, add the run identifiers, and add a
 * presenter for that output kind. A matching method id alone does not
 * promote the card or reveal a payload.
 *
 * A later read, when the research system provides it, needs:
 * - method_id and method_version
 * - output_kind matching this entry
 * - a schema-validated result for that kind
 * - executed_at, input dataset ids, and publication_allowed
 * A signed-in detail page may show the stored calculation. A signed-out
 * reader is redirected before that read. publication_allowed stays the
 * publication gate. Metadata on the list does not include the calculation.
 */

export type MethodologyTiming = "retrospective" | "contemporaneous" | "predictive";

export type MethodologyOutputKind =
  | "turning-points"
  | "time-series"
  | "regime-probabilities"
  | "nowcast"
  | "recession-probability"
  | "forecast-distribution"
  | "structural-breaks"
  | "benchmark-comparison"
  | "cross-correlation"
  | "persistence-summary"
  | "cointegration-test"
  | "stability-diagnostic"
  | "unavailable";

/** Where the card sits. `current` is work already under way. Planned groups follow the register. */
export type MethodologyGroup = "current" | "activity" | "forecasting" | "inflation" | "financial" | "structural";

/**
 * A planned entry has no research-run query. An in-development entry may query
 * run metadata. A signed-in detail page may read the stored calculation.
 * Publication still requires publication_allowed. Detecting a method id must
 * not by itself promote a card or mark a run approved for publication.
 */
export type MethodologyStage = "in-development" | "planned";

export type MethodologyCatalogueEntry = {
  slug: string;
  /** Row in docs/macro/QUANTITATIVE_METHOD_REGISTER.csv, when this card is that row. */
  registerId: string;
  name: string;
  measures: string;
  domain: string;
  timing: MethodologyTiming;
  /** Analytical job, shown on the card. Not a calculated result. */
  functionLabel: string;
  outputKind: MethodologyOutputKind;
  stage: MethodologyStage;
  group: MethodologyGroup;
  /** Identifiers this page may match in research.research_runs. Metadata only. */
  queryMethodIds: readonly string[];
  interpretation: readonly string[];
  uncertainty: readonly string[];
  dataInputs: readonly string[];
  validation: readonly string[];
  references: readonly { label: string; href: string }[];
};

export const METHODOLOGY_GROUPS: readonly { id: MethodologyGroup; heading: string; note: string }[] = [
  {
    id: "current",
    heading: "In development",
    note: "Bry–Boschan, the Stock–Watson refit, restricted coincident diffusion, Harding–Pagan characteristics, the Sahm rule, the Hamilton monthly variant, Bai–Perron mean shifts, the autoregressive benchmark, lead–lag correlations, the CPI-U autoregression, the ex-post real federal funds rate, Engle–Granger cointegration, and the CUSUM of recursive residuals have stored runs. The inflation autoregression, the subsequent ex-post real funds rate, the industrial-production CUSUM, the 10-year minus 3-month spread, and the constant-maturity spread probit are also listed. A signed-in reader can open a stored result. That is not publication approval. The Stock–Watson refit is not operationally accepted, and the preserved and unadopted historical rows are not replayable. Diffusion is not historically replayable. The Hamilton variant is not a recession label. Bai–Perron selecting no break is not a break call. The autoregression is not a qualified forecast. The holdout inflation autoregression stays insufficient because October 2025 was not interpolated. The real rate is not a Taylor rule. The spread is an indicator, not a recession probability. The probit is a separate model and is not the New York Fed model. Cointegration non-rejection is a diagnostic, not a causal claim. The two CUSUM cards are two stated specifications, not two selected break dates. Quarterly BBQ has not been run.",
  },
  {
    id: "activity",
    heading: "Economic activity and cycles",
    note: "Planned quarterly dating. Quarterly BBQ has not been run.",
  },
  {
    id: "forecasting",
    heading: "Growth and forecasting",
    note: "Planned nowcasts and the later forecasting family. US real GDP is stored as latest-revised history and no nowcast has been produced. A GDP log-growth bridge on industrial production was unstable and was not registered. A funds-rate and 10-year yield vector autoregression failed its lag and residual checks and was not registered.",
  },
  {
    id: "inflation",
    heading: "Inflation and monetary conditions",
    note: "Planned trend inflation and the Phillips curve. The CPI-U autoregression, the ex-post real federal funds rate, and the 10-year minus 3-month spread are listed under in development. The spread is an indicator, not a recession probability. The constant-maturity spread probit is a separate model, listed under in development, and is not the New York Fed model.",
  },
  {
    id: "financial",
    heading: "Financial conditions and systemic risk",
    note: "Planned summaries of financial pressure, credit and tail risk. They are not activity indexes. The required series are not stored, and they are not proxied.",
  },
  {
    id: "structural",
    heading: "Structural economic change",
    note: "The intercept-only mean-shift result and the CUSUM of recursive residuals are listed under in development. The CUSUM is not a selected break date. The general regressor model has not been estimated.",
  },
];

/**
 * Register rows that are not cards. Supporting techniques stay inside the
 * dynamic-factor family. Portfolio research is outside this catalogue.
 */
export const EXCLUDED_REGISTER_ROWS: readonly { id: string; reason: string }[] = [
  {
    id: "STATIC_PCA",
    reason: "Supporting technique for the dynamic factor. Not a separate methodology.",
  },
  {
    id: "CFNAI",
    reason: "Institutional principal-component index. Covered inside the dynamic-factor family, not a separate card.",
  },
  {
    id: "KALMAN_FILTER",
    reason: "Estimator used by a state-space model. Not a separate intelligence product.",
  },
  {
    id: "PORTFOLIO_RESEARCH",
    reason: "Deferred portfolio profile. Outside the macroeconomic methodology catalogue.",
  },
];

export const METHODOLOGY_CATALOGUE: readonly MethodologyCatalogueEntry[] = [
  {
    slug: "bry-boschan-spencer15",
    registerId: "BRY_BOSCHAN_MONTHLY",
    name: "Bry–Boschan labelled variant",
    measures:
      "Dates specific-cycle peaks and troughs in a monthly industrial-production index. The dating is retrospective. It is not a current recession forecast.",
    domain: "Economic activity",
    timing: "retrospective",
    functionLabel: "Historical dating",
    outputKind: "turning-points",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["BRY_BOSCHAN_SPENCER15_VARIANT"],
    interpretation: [
      "A peak or trough is a turning point in the dated series under this variant's rules.",
      "It does not by itself classify the wider economy as in recession, and it does not produce a probability.",
    ],
    uncertainty: [
      "This is the labelled Spencer-15 variant. It is not the 1971 programme listing and not a FORTRAN replica.",
      "The stored chronology is a full-sample retrospective dating. The centred smoother means it is not a contemporaneous recession call.",
      "Agreement with a reference chronology is not an acceptance test and is not shown here as a score.",
      "A signed-in reader can see the stored dates. They are not approved for publication.",
    ],
    dataInputs: ["Federal Reserve G.17 industrial production, total index, latest revised."],
    validation: [
      "The variant's rules and the decision to keep publication closed live in the research method, not in this page.",
      "This page does not replay the dating algorithm.",
    ],
    references: [
      {
        label: "Bry and Boschan, Cyclical analysis of time series, NBER, 1971",
        href: "https://www.nber.org/books-and-chapters/cyclical-analysis-time-series-selected-procedures-and-computer-programs",
      },
    ],
  },
  {
    slug: "stock-watson-1988",
    registerId: "STOCK_WATSON_DFM",
    name: "Stock–Watson dynamic factor",
    measures:
      "A coincident factor for economic activity in the sense of Stock and Watson's small dynamic factor model. The factor would be an estimated common movement, not an official statistic published by a statistical office.",
    domain: "Economic activity",
    timing: "contemporaneous",
    functionLabel: "Contemporaneous measurement",
    outputKind: "time-series",
    stage: "in-development",
    group: "current",
    queryMethodIds: [
      "STOCK_WATSON_COINCIDENT_1988",
      "STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT",
    ],
    interpretation: [
      "If a publication-eligible result is later supplied, it would be a time series of the estimated factor, not a single economic score.",
      "A factor path would not be a recession probability and would not be a forecast skill claim unless that is the stated output.",
    ],
    uncertainty: [
      "The modern refit estimator is registered so a later calculation can use the same method id. It is not operationally accepted. The preserved run and the unadopted re-estimate are not historically replayable, and the unadopted likelihood gain stays unadopted.",
      "The 1988 payroll specification remains blocked. Employee-hours and the 1982-dollar series are not stored.",
      "A signed-in reader sees the preserved filtered factor only when that run is stored. It is not stored on the host. The unadopted re-estimate is not plotted in its place.",
      "Loadings and the likelihood are read from the stored run. They are not approved for publication.",
      "Static principal components, the Chicago Fed National Activity Index and the Kalman filter are supporting techniques for this family. They are not separate methodologies and do not have their own cards.",
    ],
    dataInputs: [
      "The 1988 coincident specification names industrial production, real personal income less transfers, real manufacturing and trade sales, and employee-hours. This page does not decide which of those series are stored.",
    ],
    validation: [
      "Mathematical validation, historical evaluation and publication eligibility are separate. This page does not collapse them into one status.",
      "No factor chart is drawn from a dossier or from a research register.",
    ],
    references: [
      {
        label: "Stock and Watson, A probability model of the coincident economic indicators, NBER working paper 2772",
        href: "https://www.nber.org/papers/w2772",
      },
    ],
  },
  {
    slug: "diffusion-index",
    registerId: "DIFFUSION_INDEX",
    name: "Restricted coincident diffusion",
    measures:
      "Reports the share of four coincident series whose level rose over three months. It is a breadth statistic on that restricted panel. It is not a dynamic factor and not the Chicago Fed 85-indicator index.",
    domain: "Economic activity",
    timing: "contemporaneous",
    functionLabel: "Contemporaneous measurement",
    outputKind: "time-series",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["RESTRICTED_COINCIDENT_DIFFUSION"],
    interpretation: [
      "The share answers how widely a three-month rise is shared across the four series. It does not estimate a common factor.",
      "A month with a missing series omits that series from the denominator. Nothing is interpolated.",
    ],
    uncertainty: [
      "This is the restricted four-series measure. It is not the Chicago Fed 85-indicator index.",
      "A correlation with the Stock–Watson factor is not independent confirmation. The stored run is not historically replayable.",
      "The calculated share stays unpublished until publication is allowed and a presenter exists.",
    ],
    dataInputs: [
      "Industrial production, real personal income excluding transfers, real manufacturing and trade sales, and total nonfarm payroll employment, latest revised, on the balanced months used by the modern refit.",
    ],
    validation: [
      "A signed-in reader can see the stored share. Publication of the series is a separate decision.",
    ],
    references: [],
  },
  {
    slug: "harding-pagan-characteristics",
    registerId: "HARDING_PAGAN_CHARACTERISTICS",
    name: "Harding–Pagan characteristics",
    measures:
      "Reports phase duration, amplitude, and pairwise concordance from Spencer-15 turning points in monthly level series. It does not date a quarterly series, and it is not the Harding–Pagan BBQ procedure.",
    domain: "Economic activity",
    timing: "retrospective",
    functionLabel: "Historical dating",
    outputKind: "turning-points",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["HARDING_PAGAN_CHARACTERISTICS"],
    interpretation: [
      "A phase is the span from one Spencer-15 turn to the next in that series.",
      "Concordance is the share of months in which two series are in the same phase. Payroll, income, and sales turns are not NBER recession dates.",
    ],
    uncertainty: [
      "Quarterly BBQ has not been implemented. This card is not that method.",
      "The chronology is a full-sample retrospective dating on latest-revised levels. It is not a contemporaneous recession call.",
      "A signed-in reader can see the stored characteristics. They are not approved for publication.",
    ],
    dataInputs: [
      "Industrial production, real personal income excluding transfers, real manufacturing and trade sales, and total nonfarm payroll employment, as latest-revised levels.",
    ],
    validation: [
      "Dates come from the labelled Spencer-15 variant. This page does not replay that algorithm or show the dates.",
    ],
    references: [],
  },
  {
    slug: "autoregressive-benchmark",
    registerId: "AUTOREGRESSIVE_BENCHMARK",
    name: "Autoregressive benchmark",
    measures:
      "Fits an autoregression to monthly industrial-production log-growth and compares rolling-origin errors with a historical mean. A fit is a validation baseline. It is not a qualified forecast.",
    domain: "Forecasting",
    timing: "retrospective",
    functionLabel: "Benchmark comparison",
    outputKind: "benchmark-comparison",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["AUTOREGRESSIVE_BENCHMARK"],
    interpretation: [
      "The comparison is between the autoregression and the historical mean of the growth series.",
      "Beating the mean at one horizon does not qualify the method as a forecast.",
    ],
    uncertainty: [
      "The stored calculation uses the latest-revised industrial-production file. It is not a real-time forecast.",
      "The method is not empirically qualified as a forecast and is not approved for publication.",
      "A signed-in reader can see the stored comparison. It is not approved for publication.",
    ],
    dataInputs: ["Federal Reserve G.17 industrial production, total index, latest revised, as monthly log-growth."],
    validation: [
      "Lag length is chosen inside a predeclared maximum. This page does not replay the regression or show the errors.",
    ],
    references: [],
  },
  {
    slug: "lead-lag",
    registerId: "LEAD_LAG_CROSS_CORRELATION",
    name: "Lead–lag cross-correlation",
    measures:
      "Reports cross-correlations among four coincident growth rates at predeclared lags. A correlation is not a structural lead, and no series receives leading-indicator status.",
    domain: "Economic activity",
    timing: "retrospective",
    functionLabel: "Cross-correlation",
    outputKind: "cross-correlation",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["LEAD_LAG_CROSS_CORRELATION"],
    interpretation: [
      "A positive lag means the second series lags the first in the correlation.",
      "Agreement in one subsample is a stability check. It does not assign a fixed role to either series.",
    ],
    uncertainty: [
      "Significance uses a standard error that accounts for serial dependence.",
      "The correlations are estimated on latest-revised growth. They are not a real-time signal.",
      "A signed-in reader can see the stored correlations. They are not approved for publication.",
    ],
    dataInputs: [
      "Industrial production, real personal income excluding transfers, real manufacturing and trade sales, and total nonfarm payroll employment, latest revised, as monthly log-growth.",
    ],
    validation: [
      "A stored peak is not treated as a leading indicator.",
    ],
    references: [],
  },
  planned({
    slug: "harding-pagan-bbq",
    registerId: "HARDING_PAGAN_BBQ",
    name: "Harding–Pagan quarterly dating",
    measures:
      "Dates local peaks and troughs in a quarterly series, with rules for the shortest phase and cycle. It is the quarterly analogue of Bry–Boschan, not a monthly method.",
    domain: "Economic activity",
    timing: "retrospective",
    functionLabel: "Historical dating",
    outputKind: "turning-points",
    group: "activity",
    interpretation: [
      "A date would be a turning point in the quarterly series under the BBQ rules. It would not be a current-quarter forecast.",
    ],
    uncertainty: [
      "The journal article has not been line-checked. The method must not be run on monthly industrial production.",
    ],
    dataInputs: ["A quarterly series and a separate decision to date it. Euro-area GDP being stored is not that decision."],
    validation: ["No quarterly dating run exists. Overlap with a reference chronology would not be an acceptance test."],
    references: [],
  }),
  {
    slug: "sahm-rule",
    registerId: "SAHM_UNEMPLOYMENT_GAP",
    name: "Sahm rule",
    measures:
      "Measures how far the three-month average unemployment rate has risen above its low in the prior twelve months. The stored result uses the short live sample. It is not a long-history comparison.",
    domain: "Labour market",
    timing: "retrospective",
    functionLabel: "Recession association",
    outputKind: "time-series",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["SAHM_UNEMPLOYMENT_GAP"],
    interpretation: [
      "A trigger is the published association with a recession already under way. It is not an NBER determination and not a forecast.",
    ],
    uncertainty: [
      "The stored run remains the short sample. A longer revised history from January 1948 is stored and was not used for this result.",
      "October 2025 is still missing and is not interpolated. This is not a real-time Sahm evaluation.",
      "Not approved for publication.",
    ],
    dataInputs: ["US unemployment rate, latest revised, on the stored live months. A missing month fails the window."],
    validation: [
      "The existing Sahm calculator is the rule. This page reads the stored gap and does not recompute it.",
    ],
    references: [],
  },
  {
    slug: "hamilton-markov-switching",
    registerId: "HAMILTON_MARKOV_SWITCHING",
    name: "Hamilton monthly variant",
    measures:
      "Estimates two-regime probabilities for monthly industrial-production log-growth. This is a monthly variant. It is not a reproduction of Hamilton's 1989 quarterly GNP model.",
    domain: "Economic activity",
    timing: "retrospective",
    functionLabel: "Probability estimation",
    outputKind: "regime-probabilities",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["HAMILTON_MONTHLY_REGIME_SWITCHING"],
    interpretation: [
      "A regime probability is the estimated chance that the month was drawn from the lower-mean or higher-mean regime.",
      "Filtered and smoothed probabilities are separate outputs. A smoothed probability uses later months in the sample.",
    ],
    uncertainty: [
      "This is not a reproduction of the 1989 quarterly GNP model. The paper was not line-checked.",
      "Neither probability path is a real-time assessment. The input is the latest-revised index.",
      "The stored fit is replayable and is not a recession label. It is not empirically qualified and is not approved for publication.",
      "A signed-in reader can see the stored filtered probability. It is not approved for publication.",
    ],
    dataInputs: ["Federal Reserve G.17 industrial production, total index, latest revised, transformed to monthly log-growth."],
    validation: [
      "Lag length is chosen inside a predeclared set. A seeded recovery checks the estimator. It is not a recession claim.",
      "Smoothed probabilities are not plotted as if they were filtered.",
    ],
    references: [],
  },
  planned({
    slug: "mixed-frequency-nowcast",
    registerId: "MIXED_FREQUENCY_NOWCAST",
    name: "Mixed-frequency nowcast",
    measures:
      "Estimates the current quarter of a lower-frequency series from higher-frequency data. The register treats Giannone, Reichlin and Small nowcasting, and Mariano–Murasawa mixed-frequency aggregation, as this one method. Ragged-edge estimation in the sense of Bańbura and Modugno belongs to the same problem, not to a second card.",
    domain: "Forecasting",
    timing: "predictive",
    functionLabel: "Forecasting",
    outputKind: "nowcast",
    group: "forecasting",
    interpretation: [
      "A nowcast would be an estimate of a current or recent national-accounts outcome. It would not be the coincident factor.",
    ],
    uncertainty: [
      "Primary equations have not been verified. US real GDP is stored as latest-revised quarterly history. There is no vintage panel, so no nowcast has been implemented.",
    ],
    dataInputs: [
      "bea.nipa.T10106.A191RX is stored from 1947 Q1 to 2026 Q3. ALFRED vintages are not stored. Euro-area GDP is not this series.",
    ],
    validation: ["No nowcast has been calculated. A monthly factor is not a nowcast."],
    references: [],
  }),
  planned({
    slug: "advanced-forecasting",
    registerId: "ADVANCED_FORECASTING",
    name: "Advanced forecasting",
    measures:
      "A later family for conditional forecasts and impulse responses. Bayesian VARs, structural VARs, local projections and global VARs stay in one dossier. They are not four products, and cointegration or model averaging is not a separate card.",
    domain: "Forecasting",
    timing: "predictive",
    functionLabel: "Forecasting",
    outputKind: "forecast-distribution",
    group: "forecasting",
    interpretation: [
      "The intended output is a forecast distribution or a named response to a shock, depending on the specification that is eventually chosen.",
    ],
    uncertainty: [
      "No specification is selected. Mathematics for this family have not been verified in this programme.",
    ],
    dataInputs: ["Depends on the specification. No series list is fixed."],
    validation: ["There is no per-name implementation item. Nothing has been estimated."],
    references: [],
  }),
  planned({
    slug: "trend-inflation",
    registerId: "INFLATION_TREND",
    name: "Trend inflation",
    measures:
      "Separates a slow inflation component from monthly noise. A median, a trimmed mean or an unobserved-components trend could answer that question. The register has not chosen one.",
    domain: "Inflation",
    timing: "contemporaneous",
    functionLabel: "Contemporaneous measurement",
    outputKind: "time-series",
    group: "inflation",
    interpretation: [
      "The intended output is a trend time series. It is not the published twelve-month change in CPI already shown on the dashboard.",
    ],
    uncertainty: [
      "No published trend method has been selected, so no parameters exist. Trimmed-mean CPI stays blocked because component indexes are not stored.",
    ],
    dataInputs: ["US CPI is stored. A component index for a trimmed mean is not the same object and is not assumed."],
    validation: ["Nothing has been estimated. The stored CPI change is not this method."],
    references: [],
  }),
  planned({
    slug: "phillips-curve",
    registerId: "PHILLIPS_CURVE",
    name: "Phillips curve",
    measures:
      "Links inflation to a measure of economic slack. The register records the idea and does not select a specification.",
    domain: "Inflation",
    timing: "predictive",
    functionLabel: "Forecasting",
    outputKind: "time-series",
    group: "inflation",
    interpretation: [
      "A chosen specification would relate inflation to slack. It would not be an ad hoc curve fitted for the page.",
    ],
    uncertainty: [
      "No equation, slack measure, or sample has been named. Revised unemployment history is not this specification.",
    ],
    dataInputs: ["An inflation series and a slack series named by the specification. Neither choice is made."],
    validation: ["No fit exists. A near-term empirical relationship is not implied."],
    references: [],
  }),
  {
    slug: "yield-curve-probit",
    registerId: "YIELD_CURVE_PROBIT",
    name: "Constant-maturity spread recession probit",
    measures:
      "Estimates a four-quarter probit of the stored NBER classification on the 10-year minus 3-month constant-maturity spread. It is a separate model from the spread. It is not the New York Fed model and not the June 1996 Treasury-bill specification.",
    domain: "Monetary conditions",
    timing: "retrospective",
    functionLabel: "Probability estimation",
    outputKind: "recession-probability",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["CONSTANT_MATURITY_SPREAD_RECESSION_PROBIT"],
    interpretation: [
      "The outcome is the NBER quarterly classification published on 14 March 2023. It is a reference classification, not a vintage of the yields.",
      "Estimation uses spread quarters through 2005 Q4. Evaluation uses spread quarters from 2006 Q1. Those windows stay fixed.",
    ],
    uncertainty: [
      "This is not the New York Fed parameterisation.",
      "The short rate is the H.15 three-month constant-maturity yield, not the three-month Treasury bill in the June 1996 article.",
      "An unstable or perfectly separated fit is stored as such. No probability is invented.",
      "A signed-out session does not receive the calculation. Publication stays closed.",
    ],
    dataInputs: [
      "Latest revised H.15 10-year and 3-month constant-maturity yields, and the attributed NBER chronology dated 14 March 2023.",
    ],
    validation: [
      "This page reads the stored fit. It does not move the estimation or evaluation windows, and it does not re-estimate the probit.",
    ],
    references: [
      {
        label: "NBER US business cycle expansions and contractions, page dated 14 March 2023",
        href: "https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions",
      },
    ],
  },
  planned({
    slug: "financial-conditions",
    registerId: "FINANCIAL_CONDITIONS",
    name: "Financial conditions index",
    measures:
      "Summarises financial pressure in one index. An institutional example is the Chicago Fed National Financial Conditions Index. Aqil has not adopted that formula.",
    domain: "Financial conditions",
    timing: "contemporaneous",
    functionLabel: "Contemporaneous measurement",
    outputKind: "time-series",
    group: "financial",
    interpretation: [
      "The intended output is a financial-pressure time series. It is not a measure of real activity.",
    ],
    uncertainty: ["The formula has not been verified. No financial-conditions series list is contracted."],
    dataInputs: ["The series a chosen index requires. Those series are not named, so none are being collected for this method."],
    validation: ["No index has been calculated."],
    references: [],
  }),
  planned({
    slug: "excess-bond-premium",
    registerId: "GILCHRIST_ZAKRAJSEK_EBP",
    name: "Gilchrist–Zakrajšek excess bond premium",
    measures:
      "Measures the part of a corporate bond spread that remains after an allowance for expected default. It is a credit-market risk premium, not a Treasury spread.",
    domain: "Credit conditions",
    timing: "contemporaneous",
    functionLabel: "Contemporaneous measurement",
    outputKind: "time-series",
    group: "financial",
    interpretation: [
      "The intended output is the excess bond premium over time. It is not a recession probability by itself.",
    ],
    uncertainty: ["The 2012 paper has not been line-checked. Corporate bond and default inputs are not stored."],
    dataInputs: ["Corporate bond prices and an expected-default measure from a rights-cleared source. Both are absent."],
    validation: ["No premium has been calculated."],
    references: [],
  }),
  planned({
    slug: "credit-to-gdp-gap",
    registerId: "BIS_CREDIT_GAP",
    name: "Credit-to-GDP gap",
    measures:
      "Compares credit to GDP with a slow trend, as in the BIS early-warning gap. The stored BIS dollar-credit series is not that gap.",
    domain: "Credit conditions",
    timing: "contemporaneous",
    functionLabel: "Contemporaneous measurement",
    outputKind: "time-series",
    group: "financial",
    interpretation: [
      "The intended output is a gap, in the units the BIS definition uses. It is not the level of bank credit already on the dashboard.",
    ],
    uncertainty: ["The BIS formula has not been verified against the current documentation in this pass."],
    dataInputs: ["Credit and GDP on the BIS definitions. The stored US dollar credit to non-banks is a different object."],
    validation: ["No gap has been calculated. The stored credit level must not be relabelled as the gap."],
    references: [],
  }),
  planned({
    slug: "growth-at-risk",
    registerId: "GROWTH_AT_RISK",
    name: "Growth-at-risk",
    measures:
      "Describes the lower tail of future growth conditional on financial conditions. It is a distributional forecast, not a mean nowcast.",
    domain: "Forecasting",
    timing: "predictive",
    functionLabel: "Forecasting",
    outputKind: "forecast-distribution",
    group: "financial",
    interpretation: [
      "The intended output is a lower-tail growth figure or a forecast distribution. It is not a point forecast of GDP by itself.",
    ],
    uncertainty: ["The Adrian, Boyarchenko and Giannone equations have not been verified. The method stays later in the programme."],
    dataInputs: ["A growth outcome and a financial-conditions measure. Neither input is contracted for this method."],
    validation: ["No tail forecast exists."],
    references: [],
  }),
  {
    slug: "bai-perron-breaks",
    registerId: "BAI_PERRON_BREAKS",
    name: "Bai–Perron mean shifts",
    measures:
      "Searches monthly industrial-production log-growth for intercept-only mean shifts. This is not the general Bai–Perron regressor model. Retrospective detection is not a forecast.",
    domain: "Structural change",
    timing: "retrospective",
    functionLabel: "Structural analysis",
    outputKind: "structural-breaks",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["BAI_PERRON_MEAN_SHIFTS"],
    interpretation: [
      "The selected model is the break count chosen by the primary trimming rule.",
      "A looser trim that changes the count is stored sensitivity. It is not a second selected model.",
    ],
    uncertainty: [
      "The 1998 and 2003 papers were not line-checked.",
      "Dates, when a break is selected, are point estimates. No confidence interval is attached.",
      "The result uses the latest-revised file. Selecting no break is not a break call and is not approved for publication.",
    ],
    dataInputs: ["Federal Reserve G.17 industrial production, total index, latest revised, as monthly log-growth."],
    validation: [
      "The primary minimum segment is the larger of 24 months and 15 percent of the sample.",
      "A signed-in reader can see the stored selection. A looser trim is sensitivity, not a second model.",
    ],
    references: [],
  },
  {
    slug: "cpi-u-inflation-autoregression",
    registerId: "CPI_U_INFLATION_AUTREGRESSION",
    name: "CPI-U inflation autoregression",
    measures:
      "Fits an autoregression to the monthly log change of CPI-U and reports the ordinary least squares sum of the autoregressive coefficients. The fit is not a forecast and not the Andrews–Chen median-unbiased estimator.",
    domain: "Inflation",
    timing: "retrospective",
    functionLabel: "Persistence summary",
    outputKind: "persistence-summary",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["CPI_U_INFLATION_AUTREGRESSION"],
    interpretation: [
      "The lag is the one chosen by AIC inside the predeclared maximum.",
      "Persistence is the sum of the ordinary least squares coefficients, excluding the intercept.",
    ],
    uncertainty: [
      "The modelled series is the monthly log change. It is not the twelve-month percent change.",
      "October 2025 CPI is missing and is not interpolated.",
      "The stored figure is not the Andrews–Chen median-unbiased estimator and is not a forecast.",
      "A signed-in reader can see the stored fit. It is not approved for publication.",
    ],
    dataInputs: ["US CPI-U, seasonally adjusted, latest revised, as monthly log changes."],
    validation: [
      "This page reads the stored lag and persistence. It does not replay the regression.",
    ],
    references: [],
  },
  {
    slug: "ex-post-real-federal-funds-rate",
    registerId: "EX_POST_REAL_FEDERAL_FUNDS_RATE",
    name: "Ex-post real federal funds rate",
    measures:
      "Subtracts trailing twelve-month CPI-U inflation from the federal funds rate in the same month. The result is an ex-post identity. It is not a Taylor rule and not an ex-ante real rate.",
    domain: "Monetary conditions",
    timing: "retrospective",
    functionLabel: "Contemporaneous measurement",
    outputKind: "time-series",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["EX_POST_REAL_FEDERAL_FUNDS_RATE"],
    interpretation: [
      "The real rate is the funds rate minus realised inflation over the previous twelve months.",
      "A positive reading is not a policy prescription.",
    ],
    uncertainty: [
      "Inflation is a percent change of the index, not a monthly log change.",
      "No output gap is estimated. This is not a Taylor rule and not an ex-ante rate.",
      "A signed-in reader can see the stored identity. It is not approved for publication.",
    ],
    dataInputs: [
      "Federal funds rate, latest revised, and CPI-U, latest revised, aligned on the same month.",
    ],
    validation: [
      "This page reads the stored funds rate, inflation, and real rate. It does not recompute them.",
    ],
    references: [],
  },
  {
    slug: "engle-granger-cointegration",
    registerId: "ENGLE_GRANGER_COINTEGRATION",
    name: "Engle–Granger cointegration",
    measures:
      "Tests whether the log levels of industrial production and payroll employment share a cointegrating residual. A failure to reject no-cointegration is a result. It is not a causal claim.",
    domain: "Economic activity",
    timing: "retrospective",
    functionLabel: "Structural analysis",
    outputKind: "cointegration-test",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["ENGLE_GRANGER_COINTEGRATION"],
    interpretation: [
      "The null is no cointegration. The reported comparison is with the MacKinnon five percent critical value for two series and a constant.",
      "The normalisation is predeclared. It does not assign a cause.",
    ],
    uncertainty: [
      "The inputs are latest-revised log levels. Growth-rate lead–lag is not repeated here as causality.",
      "A signed-in reader can see the stored test. It is not approved for publication.",
    ],
    dataInputs: [
      "Industrial production and total nonfarm payroll employment, latest revised, as natural log levels.",
    ],
    validation: [
      "This page reads the stored statistic and critical value. It does not rerun the test.",
    ],
    references: [],
  },
  {
    slug: "cusum-recursive-residuals",
    registerId: "CUSUM_RECURSIVE_RESIDUALS",
    name: "CUSUM of recursive residuals",
    measures:
      "Compares the CUSUM of recursive residuals from a predeclared industrial-production log-growth autoregression with a five percent boundary. Staying inside the boundary is a result. It is not a selected break date.",
    domain: "Structural change",
    timing: "retrospective",
    functionLabel: "Structural analysis",
    outputKind: "stability-diagnostic",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["CUSUM_RECURSIVE_RESIDUALS"],
    interpretation: [
      "A crossing would be an absolute CUSUM outside the conventional five percent boundary.",
      "The largest absolute CUSUM is a point on that path. It is not a break date.",
    ],
    uncertainty: [
      "The lag is predeclared. It is not the lag selected by the autoregressive benchmark.",
      "The input is latest-revised log-growth. This is not a real-time stability test.",
      "A signed-in reader can see the stored comparison. It is not approved for publication.",
    ],
    dataInputs: ["Federal Reserve G.17 industrial production, total index, latest revised, as monthly log-growth."],
    validation: [
      "This page reads the stored CUSUM extreme and the boundary at that month. It does not rerun the recursion.",
    ],
    references: [],
  },
  {
    slug: "inflation-autoregression",
    registerId: "INFLATION_AUTOREGRESSION",
    name: "CPI-U inflation autoregression",
    measures:
      "Fits an autoregression to the monthly logarithmic change in CPI-U and compares held-out errors with the historical mean. A fit is not a product forecast and not a Taylor rule.",
    domain: "Inflation",
    timing: "retrospective",
    functionLabel: "Persistence summary",
    outputKind: "persistence-summary",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["INFLATION_AUTOREGRESSION"],
    interpretation: [
      "The lag is chosen by AIC on the pre-holdout sample, inside a predeclared maximum.",
      "Persistence is the sum of the slope coefficients. A half-life is shown only when that sum is between 0 and 1.",
    ],
    uncertainty: [
      "The modelled series is the monthly logarithmic change. It is not the twelve-month percent change.",
      "Beating the historical mean at one horizon does not qualify the method as a forecast. The stored holdout is insufficient because October 2025 was not interpolated.",
      "This is not a Taylor rule. A signed-in reader can see the stored fit. It is not approved for publication.",
    ],
    dataInputs: ["US CPI-U, seasonally adjusted, latest revised, as monthly logarithmic changes."],
    validation: [
      "This page reads the stored lag, persistence, and horizon comparison. It does not replay the regression.",
    ],
    references: [],
  },
  {
    slug: "ex-post-real-funds-rate",
    registerId: "EX_POST_REAL_FUNDS_RATE",
    name: "Ex-post real federal funds rate",
    measures:
      "Subtracts CPI-U inflation over the following twelve months from the federal funds rate in month t. The result is retrospective. It is not a Taylor rule.",
    domain: "Monetary conditions",
    timing: "retrospective",
    functionLabel: "Contemporaneous measurement",
    outputKind: "time-series",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["EX_POST_REAL_FUNDS_RATE"],
    interpretation: [
      "Inflation uses the CPI-U index at month t and twelve months later. It is subsequent to the funds rate.",
      "A positive reading is not a policy prescription.",
    ],
    uncertainty: [
      "The real rate at month t uses a price index that was not known at month t.",
      "No output gap or inflation target is estimated. This is not a Taylor rule.",
      "A signed-in reader can see the stored identity. It is not approved for publication.",
    ],
    dataInputs: [
      "Federal funds effective rate, latest revised, and CPI-U, latest revised, twelve months apart.",
    ],
    validation: [
      "This page reads the stored funds rate, subsequent inflation, and real rate. It does not recompute them.",
    ],
    references: [],
  },
  {
    slug: "ip-growth-cusum",
    registerId: "IP_GROWTH_CUSUM",
    name: "Industrial-production CUSUM",
    measures:
      "Compares the CUSUM of recursive residuals from a predeclared lag-1 autoregression of industrial-production log-growth with a five percent boundary. Staying inside the boundary is a result. It is not a selected break date and not a Bai–Perron mean shift.",
    domain: "Structural change",
    timing: "retrospective",
    functionLabel: "Structural analysis",
    outputKind: "stability-diagnostic",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["IP_GROWTH_CUSUM"],
    interpretation: [
      "A crossing is a cumulative sum strictly outside the returned five percent boundary.",
      "The largest absolute CUSUM is a point on that path. It is not a break date.",
    ],
    uncertainty: [
      "The lag is predeclared at 1. An information criterion does not choose it.",
      "The input is latest-revised log-growth. This is not a real-time stability test and not a Bai–Perron search.",
      "A signed-in reader can see the stored comparison. It is not approved for publication.",
    ],
    dataInputs: ["Federal Reserve G.17 industrial production, total index, latest revised, as monthly log-growth."],
    validation: [
      "This page reads the stored CUSUM extreme and the boundary at that month. It does not rerun the recursion.",
    ],
    references: [],
  },
  {
    slug: "estrella-mishkin-spread",
    registerId: "ESTRELLA_MISHKIN_TERM_SPREAD",
    name: "10-year minus 3-month spread",
    measures:
      "Reports the latest revised difference between the 10-year and 3-month constant-maturity yields. It is not a recession probability.",
    domain: "Monetary conditions",
    timing: "retrospective",
    functionLabel: "Yield spread",
    outputKind: "time-series",
    stage: "in-development",
    group: "current",
    queryMethodIds: ["ESTRELLA_MISHKIN_TERM_SPREAD"],
    interpretation: [
      "The spread is the 10-year investment-basis yield minus the 3-month investment-basis yield.",
      "The June 1996 article states a horizon. This page does not turn the spread into a probability.",
    ],
    uncertainty: [
      "No probit coefficients were estimated. The article does not print them.",
      "The 3-month series is not the discount-basis Treasury bill, and the federal funds rate is not the short rate.",
      "A signed-in reader can see the stored spread. It is not approved for publication.",
    ],
    dataInputs: [
      "Latest revised H.15 10-year and 3-month constant-maturity yields, both quoted on an investment basis.",
    ],
    validation: [
      "This page reads the stored yields and their difference. It does not estimate a probit.",
    ],
    references: [],
  },
];

function planned(
  entry: Omit<MethodologyCatalogueEntry, "stage" | "queryMethodIds">,
): MethodologyCatalogueEntry {
  return { ...entry, stage: "planned", queryMethodIds: [] };
}

export function methodologyBySlug(slug: string): MethodologyCatalogueEntry | undefined {
  return METHODOLOGY_CATALOGUE.find((entry) => entry.slug === slug);
}

export function methodologyQueryIds(): string[] {
  const ids: string[] = [];
  for (const entry of METHODOLOGY_CATALOGUE) {
    for (const id of entry.queryMethodIds) {
      if (!ids.includes(id)) ids.push(id);
    }
  }
  return ids;
}
