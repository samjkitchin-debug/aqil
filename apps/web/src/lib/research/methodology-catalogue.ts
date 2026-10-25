/**
 * User-facing methodology register.
 *
 * Descriptions are the research question. They are not calculated results.
 * Live numbers must come from a publication-eligible, typed model result.
 * This module does not read dossiers, CSV registers, or calculation JSON.
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
 * The web shows the result only when publication_allowed is true and a
 * presenter exists for that output_kind. Until then, run metadata is enough.
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
  | "unavailable";

/** Where the card sits. `current` is work already under way. Planned groups follow the register. */
export type MethodologyGroup = "current" | "activity" | "forecasting" | "inflation" | "financial" | "structural";

/**
 * A planned entry has no research-run query. An in-development entry may query
 * run metadata. Publication of a payload still requires publication_allowed
 * and a presenter. Detecting a method id must not by itself promote a card.
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
    note: "These two methods have implementation work. A stored run is described only as far as its publication state allows. The backlog does not open another methodology while the Stock–Watson refit remains partial and unpublished.",
  },
  {
    id: "activity",
    heading: "Economic activity and cycles",
    note: "Planned dating, breadth and regime methods. None of these has a stored Aqil calculation.",
  },
  {
    id: "forecasting",
    heading: "Growth and forecasting",
    note: "Planned nowcasts and the later forecasting family. No forecast has been produced.",
  },
  {
    id: "inflation",
    heading: "Inflation and monetary conditions",
    note: "Planned inflation and yield-curve methods. No specification in this group has been selected for estimation.",
  },
  {
    id: "financial",
    heading: "Financial conditions and systemic risk",
    note: "Planned summaries of financial pressure, credit and tail risk. They are not activity indexes.",
  },
  {
    id: "structural",
    heading: "Structural economic change",
    note: "A planned test for whether a named relationship has shifted. No relationship has been named for estimation.",
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
      "Agreement with a reference chronology is not an acceptance test and is not shown here as a score.",
      "The calculated dates stay unpublished until the research system marks a run eligible and a turning-point presenter exists.",
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
      "The method registry shipped with this application does not register a factor estimator.",
      "Another part of the programme may be writing runs under the identifiers below. This page does not read those working files.",
      "Loadings, likelihood and the factor path are not selected, even when a run row exists.",
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
  planned({
    slug: "diffusion-index",
    registerId: "DIFFUSION_INDEX",
    name: "Diffusion index",
    measures:
      "Reports the share of a named panel that is improving. It is a breadth statistic, not a dynamic factor and not a recession call.",
    domain: "Economic activity",
    timing: "contemporaneous",
    functionLabel: "Contemporaneous measurement",
    outputKind: "time-series",
    group: "activity",
    interpretation: [
      "A diffusion index answers how widely a movement is shared. It does not estimate a common factor.",
    ],
    uncertainty: [
      "The register has not chosen the panel or the formula. No Aqil diffusion series exists.",
    ],
    dataInputs: ["A defined panel with a common history. That panel is not fixed in the register."],
    validation: ["No specification is documented, so nothing has been validated."],
    references: [],
  }),
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
  planned({
    slug: "hamilton-markov-switching",
    registerId: "HAMILTON_MARKOV_SWITCHING",
    name: "Hamilton Markov-switching model",
    measures:
      "Estimates the probability that a series, or a factor, is in one of a small number of regimes. Hamilton's 1989 model is the established reference. Aqil has not fitted it.",
    domain: "Economic activity",
    timing: "contemporaneous",
    functionLabel: "Probability estimation",
    outputKind: "regime-probabilities",
    group: "activity",
    interpretation: [
      "The intended output is a probability of a regime, not a turning-point date and not a single activity score.",
    ],
    uncertainty: [
      "The paper has not been line-checked for this programme. There is no estimated transition matrix.",
    ],
    dataInputs: ["A dated activity series or a factor, once that object exists. The estimation stack is not in place."],
    validation: ["No implementation task is open. Nothing has been validated."],
    references: [],
  }),
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
      "Primary equations have not been verified. US GDP is not stored. This does not start before the dynamic-factor data contract.",
    ],
    dataInputs: ["A target quarterly series and the monthly series the chosen specification names. Those inputs are not assembled."],
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
    uncertainty: ["No published trend method has been selected, so no parameters exist."],
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
    uncertainty: ["No equation, slack measure or sample has been named."],
    dataInputs: ["An inflation series and a slack series named by the specification. Neither choice is made."],
    validation: ["No fit exists. A near-term empirical relationship is not implied."],
    references: [],
  }),
  planned({
    slug: "yield-curve-probit",
    registerId: "YIELD_CURVE_PROBIT",
    name: "Yield-curve recession probability",
    measures:
      "Estimates the probability of a future recession from the term spread, in the sense of Estrella and Mishkin. The federal funds rate is not a substitute for the three-month yield.",
    domain: "Monetary conditions",
    timing: "predictive",
    functionLabel: "Probability estimation",
    outputKind: "recession-probability",
    group: "inflation",
    interpretation: [
      "The intended output is a probability of a stated future recession event. It is not a dating of past turning points.",
    ],
    uncertainty: [
      "The paper has not been line-checked. The three-month Treasury yield required by the later task is not stored.",
    ],
    dataInputs: ["A rights-cleared three-month yield and the longer yield the specification names. Acquisition has not started."],
    validation: ["The probit is unimplemented. No probability is shown."],
    references: [],
  }),
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
  planned({
    slug: "bai-perron-breaks",
    registerId: "BAI_PERRON_BREAKS",
    name: "Bai–Perron structural breaks",
    measures:
      "Searches a linear relationship for more than one break date, following Bai and Perron. It asks whether that relationship has shifted. It is not an activity index.",
    domain: "Structural change",
    timing: "retrospective",
    functionLabel: "Structural analysis",
    outputKind: "structural-breaks",
    group: "structural",
    interpretation: [
      "The intended output is a chronology of break dates in a named relationship, with the uncertainty the method states.",
    ],
    uncertainty: ["The paper has not been line-checked. No relationship has been named, so there is nothing to split."],
    dataInputs: ["The dependent and explanatory series of a named relationship. They are not chosen."],
    validation: ["No break test has been run."],
    references: [],
  }),
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
