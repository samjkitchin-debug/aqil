export type LiveSeriesRetrieval = {
  sourceId: string;
  datasetId: string;
  retrievedAt: string;
  seriesProvenance: string;
  unit: string;
  seasonalAdjustment: string;
  frequency: string;
  periods: string[];
  latestPeriod: string;
  latestRawValue: string;
};

export type SeriesBriefingCopy = {
  heading: string;
  notice: string;
  sourceLine: string;
  spanLine: string;
  latestLine: string;
  gapLine: string | null;
  freshnessLine: string;
};

const MONTH = new Intl.DateTimeFormat("en-GB", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

const RETRIEVED = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

export function unpublishedMonths(periods: readonly string[]): string[] {
  if (periods.length === 0) return [];
  const present = new Set(periods.map(monthKey));
  const sorted = [...present].sort();
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  if (!first || !last) return [];
  const gaps: string[] = [];
  let cursor = first;
  while (cursor <= last) {
    if (!present.has(cursor)) gaps.push(cursor);
    cursor = nextMonth(cursor);
  }
  return gaps;
}

export function presentSeriesBriefing(series: LiveSeriesRetrieval): SeriesBriefingCopy {
  const periods = [...series.periods].sort();
  const first = periods[0] ?? series.latestPeriod;
  const last = periods[periods.length - 1] ?? series.latestPeriod;
  const gaps = unpublishedMonths(periods);
  const provenance = sentenceStart(series.seriesProvenance.replaceAll("_", " "));
  return {
    heading: "Historical monthly series",
    notice: "Stored economic data from one retrieval. Not a news announcement and not an investment conclusion.",
    sourceLine: `Source ${series.sourceId}. Dataset ${series.datasetId}. ${provenance}, ${series.seasonalAdjustment.replaceAll("_", " ")}, ${series.unit}.`,
    spanLine: `${periods.length} monthly observations from ${formatMonth(first)} to ${formatMonth(last)}.`,
    latestLine: `Latest observation in this retrieval: ${formatMonth(series.latestPeriod)}, ${series.latestRawValue} ${series.unit}.`,
    gapLine: gaps.length === 0 ? null : gapSentence(gaps),
    freshnessLine: `Retrieved ${formatRetrieved(series.retrievedAt)}.`,
  };
}

function gapSentence(gaps: readonly string[]): string {
  const permanent = gaps.filter((gap) => gap === "2025-10");
  const other = gaps.filter((gap) => gap !== "2025-10");
  const parts: string[] = [];
  if (permanent.length > 0) {
    parts.push(
      "Permanently missing: October 2025. The Bureau of Labor Statistics did not publish this month.",
    );
  }
  if (other.length > 0) {
    parts.push(`Not published in this retrieval: ${other.map(formatMonth).join(", ")}.`);
  }
  parts.push("Nothing was filled in.");
  return parts.join(" ");
}

function sentenceStart(value: string): string {
  if (value.length === 0) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function monthKey(isoDate: string): string {
  return isoDate.slice(0, 7);
}

function nextMonth(key: string): string {
  const [yearText, monthText] = key.split("-");
  const year = Number(yearText);
  const month = Number(monthText);
  if (month === 12) return `${year + 1}-01`;
  return `${year}-${String(month + 1).padStart(2, "0")}`;
}

function formatMonth(isoOrKey: string): string {
  const key = isoOrKey.slice(0, 7);
  const date = new Date(`${key}-01T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return isoOrKey;
  return MONTH.format(date);
}

function formatRetrieved(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${RETRIEVED.format(date)} UTC`;
}
