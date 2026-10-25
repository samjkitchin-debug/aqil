import type { MethodologyCatalogueEntry } from "./methodology-catalogue.ts";

/** Run metadata. Calculation payloads are intentionally absent. */
export type MethodologyRunMeta = {
  methodId: string;
  methodVersion: string;
  executedAt: string;
  executionStatus: string;
  publicationAllowed: boolean;
  dataSufficiency: string;
};

export type MethodologyRunLoad =
  | { status: "ready"; runs: readonly MethodologyRunMeta[] }
  | { status: "unavailable"; reason: string };

export type MethodologySection = {
  id: string;
  heading: string;
  paragraphs: readonly string[];
};

export type MethodologyPresentation = {
  slug: string;
  name: string;
  measures: string;
  domain: string;
  timingLabel: string;
  functionLabel: string;
  outputLabel: string;
  statusLine: string;
  latestLine: string | null;
  sections: readonly MethodologySection[];
  references: MethodologyCatalogueEntry["references"];
};

const EXECUTED = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

const TIMING_LABEL: Record<MethodologyCatalogueEntry["timing"], string> = {
  retrospective: "Retrospective",
  contemporaneous: "Contemporaneous",
  predictive: "Predictive",
};

const OUTPUT_LABEL: Record<MethodologyCatalogueEntry["outputKind"], string> = {
  "turning-points": "Turning-point chronology",
  "time-series": "Time series",
  "regime-probabilities": "Regime probabilities",
  nowcast: "Current-quarter estimate",
  "recession-probability": "Recession probability",
  "forecast-distribution": "Forecast distribution",
  "structural-breaks": "Structural-break chronology",
  unavailable: "No output type is defined",
};

export function presentMethodology(
  entry: MethodologyCatalogueEntry,
  load: MethodologyRunLoad,
): MethodologyPresentation {
  if (entry.stage === "planned") return presentPlanned(entry);
  const matched = load.status === "ready" ? runsFor(entry, load.runs) : [];
  const latest = matched[0] ?? null;
  const statusLine = statusLineFor(entry, load, latest, matched.length);
  return {
    slug: entry.slug,
    name: entry.name,
    measures: entry.measures,
    domain: entry.domain,
    timingLabel: TIMING_LABEL[entry.timing],
    functionLabel: entry.functionLabel,
    outputLabel: OUTPUT_LABEL[entry.outputKind],
    statusLine,
    latestLine: latest ? latestLine(latest) : null,
    references: entry.references,
    sections: [
      { id: "overview", heading: "Overview", paragraphs: [entry.measures] },
      {
        id: "current-result",
        heading: "Current result",
        paragraphs: [currentResult(entry, load, latest)],
      },
      {
        id: "historical-output",
        heading: "Historical output",
        paragraphs: [historicalOutput(entry, latest)],
      },
      { id: "interpretation", heading: "Interpretation", paragraphs: entry.interpretation },
      { id: "uncertainty", heading: "Confidence and uncertainty", paragraphs: entry.uncertainty },
      { id: "data", heading: "Data", paragraphs: entry.dataInputs },
      { id: "validation", heading: "Validation", paragraphs: entry.validation },
      {
        id: "operations",
        heading: "Operational status",
        paragraphs: [operationalStatus(load, latest, matched.length)],
      },
      {
        id: "technical",
        heading: "Technical evidence",
        paragraphs: technicalEvidence(entry, load, latest),
      },
    ],
  };
}

function presentPlanned(entry: MethodologyCatalogueEntry): MethodologyPresentation {
  const intended = OUTPUT_LABEL[entry.outputKind];
  return {
    slug: entry.slug,
    name: entry.name,
    measures: entry.measures,
    domain: entry.domain,
    timingLabel: TIMING_LABEL[entry.timing],
    functionLabel: entry.functionLabel,
    outputLabel: intended,
    statusLine: "Planned.",
    latestLine: null,
    references: entry.references,
    sections: [
      { id: "overview", heading: "Overview", paragraphs: [entry.measures] },
      {
        id: "current-result",
        heading: "Current result",
        paragraphs: [
          "Aqil has not calculated this methodology. There is no factor, no reading, no chronology, no probability, no parameter set and no execution time.",
        ],
      },
      {
        id: "historical-output",
        heading: "Intended output",
        paragraphs: [
          `If this method is later implemented and publication is allowed, the output type would be: ${intended}. That output does not exist.`,
        ],
      },
      { id: "interpretation", heading: "What it would answer", paragraphs: entry.interpretation },
      { id: "uncertainty", heading: "Limits", paragraphs: entry.uncertainty },
      { id: "data", heading: "Data", paragraphs: entry.dataInputs },
      { id: "validation", heading: "Validation", paragraphs: entry.validation },
      {
        id: "operations",
        heading: "Operational status",
        paragraphs: ["Planned. There is no schedule, no stored run and no publication decision."],
      },
    ],
  };
}

function runsFor(
  entry: MethodologyCatalogueEntry,
  runs: readonly MethodologyRunMeta[],
): MethodologyRunMeta[] {
  return runs
    .filter((run) => entry.queryMethodIds.includes(run.methodId))
    .slice()
    .sort((a, b) => Date.parse(b.executedAt) - Date.parse(a.executedAt));
}

function statusLineFor(
  entry: MethodologyCatalogueEntry,
  load: MethodologyRunLoad,
  latest: MethodologyRunMeta | null,
  count: number,
): string {
  if (entry.queryMethodIds.length === 0) {
    return "No method identifier is registered for this page.";
  }
  if (load.status === "unavailable") return load.reason;
  if (!latest) return "No stored run matches this methodology.";
  if (!latest.publicationAllowed) {
    return count === 1
      ? "One stored run. The calculated output is not eligible for publication."
      : `${count} stored runs. The calculated output is not eligible for publication.`;
  }
  return "A publication-eligible run is stored. This page has no presenter for its output.";
}

function currentResult(
  entry: MethodologyCatalogueEntry,
  load: MethodologyRunLoad,
  latest: MethodologyRunMeta | null,
): string {
  if (load.status === "unavailable") {
    return "The current result cannot be described because run metadata could not be read. No output is invented in its place.";
  }
  if (!latest) {
    return `No stored run is available for ${entry.name}. Nothing is plotted.`;
  }
  if (!latest.publicationAllowed) {
    return "The latest run is stored and its calculated output is withheld. Publication is closed, so this page does not show dates, factor values, probabilities or scores from that run.";
  }
  return "Publication is open for the latest run, but no typed presenter is wired for this output. The figures stay hidden until that presenter exists.";
}

function historicalOutput(entry: MethodologyCatalogueEntry, latest: MethodologyRunMeta | null): string {
  if (!latest || !latest.publicationAllowed) {
    if (entry.outputKind === "turning-points") {
      return "A published result would be a chronology of peaks and troughs. That chronology is not shown.";
    }
    if (entry.outputKind === "time-series") {
      return "A published result would be a time series. That series is not shown.";
    }
    return `A published result would be: ${OUTPUT_LABEL[entry.outputKind]}. That output is not shown.`;
  }
  return "A publication-eligible run exists. Historical output stays hidden until a presenter for this output type exists.";
}

function operationalStatus(
  load: MethodologyRunLoad,
  latest: MethodologyRunMeta | null,
  count: number,
): string {
  if (load.status === "unavailable") {
    return `${load.reason} Hosted scheduling is not read by this page.`;
  }
  if (!latest) {
    return "No execution time is stored for the identifiers this page queries. This page does not report a schedule it cannot read.";
  }
  const when = formatExecuted(latest.executedAt);
  return `${count === 1 ? "The stored execution" : "The latest stored execution"} was ${when}. Execution status ${latest.executionStatus}. Data sufficiency ${latest.dataSufficiency}. A stored execution is not a hosted schedule.`;
}

function technicalEvidence(
  entry: MethodologyCatalogueEntry,
  load: MethodologyRunLoad,
  latest: MethodologyRunMeta | null,
): string[] {
  const lines = [
    `Query identifiers: ${entry.queryMethodIds.join(", ")}.`,
    "Calculation JSON, payload hashes and model coefficients are not loaded.",
  ];
  if (load.status === "unavailable") {
    lines.push(load.reason);
    return lines;
  }
  if (!latest) {
    lines.push("No matching run row.");
    return lines;
  }
  lines.push(`Latest method ${latest.methodId} ${latest.methodVersion}.`);
  lines.push(`Publication allowed: ${latest.publicationAllowed ? "yes" : "no"}.`);
  lines.push(`Executed ${formatExecuted(latest.executedAt)}.`);
  return lines;
}

function latestLine(run: MethodologyRunMeta): string {
  return `${run.methodId} ${run.methodVersion}, executed ${formatExecuted(run.executedAt)}.`;
}

function formatExecuted(value: string): string {
  const when = new Date(value);
  if (Number.isNaN(when.getTime())) return value;
  return `${EXECUTED.format(when)} UTC`;
}
