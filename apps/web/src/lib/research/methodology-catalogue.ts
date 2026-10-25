/**
 * User-facing methodology register.
 *
 * Descriptions are the research question. They are not calculated results.
 * Live numbers must come from a publication-eligible, typed model result.
 * This module does not read dossiers, CSV registers, or calculation JSON.
 *
 * A later read, when the research system provides it, needs:
 * - method_id and method_version
 * - output_kind: turning_points | time_series | probability | nowcast | state
 * - a schema-validated result for that kind
 * - executed_at, input dataset ids, and publication_allowed
 * The web shows the result only when publication_allowed is true and a
 * presenter exists for that output_kind. Until then, run metadata is enough.
 */

export type MethodologyTiming = "retrospective" | "contemporaneous" | "predictive";

export type MethodologyOutputKind = "turning-points" | "time-series" | "unavailable";

export type MethodologyCatalogueEntry = {
  slug: string;
  name: string;
  measures: string;
  domain: string;
  timing: MethodologyTiming;
  outputKind: MethodologyOutputKind;
  /** Identifiers this page may match in research.research_runs. Metadata only. */
  queryMethodIds: readonly string[];
  interpretation: readonly string[];
  uncertainty: readonly string[];
  dataInputs: readonly string[];
  validation: readonly string[];
  references: readonly { label: string; href: string }[];
};

export const METHODOLOGY_CATALOGUE: readonly MethodologyCatalogueEntry[] = [
  {
    slug: "bry-boschan-spencer15",
    name: "Bry–Boschan labelled variant",
    measures:
      "Dates specific-cycle peaks and troughs in a monthly industrial-production index. The dating is retrospective. It is not a current recession forecast.",
    domain: "Economic activity",
    timing: "retrospective",
    outputKind: "turning-points",
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
    name: "Stock–Watson dynamic factor",
    measures:
      "A coincident factor for economic activity in the sense of Stock and Watson's small dynamic factor model. The factor would be an estimated common movement, not an official statistic published by a statistical office.",
    domain: "Economic activity",
    timing: "contemporaneous",
    outputKind: "time-series",
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
];

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
