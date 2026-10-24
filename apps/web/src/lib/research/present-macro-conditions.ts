import {
  MACRO_CONDITIONS_WINDOW,
  MACRO_SERIES,
  MONTHLY_STALE_MONTHS,
  QUARTERLY_STALE_QUARTERS,
  UNAVAILABLE_CONDITIONS,
  WEEKLY_STALE_DAYS,
  type StoredObservation,
  type StoredSeriesWindow,
} from "./macro-conditions.ts";
import {
  SERIES_PAGE_UNAVAILABLE,
  indicatorMetadata,
  type IndicatorMetadata,
} from "./indicator-metadata.ts";
import {
  displayChange,
  displayLevel,
  storedUnitPhrase,
  type DisplayLevel,
} from "./format-indicator.ts";
import { buildSeriesChart, periodsAreAdjacent, type SeriesChartModel } from "./series-chart-model.ts";

export type SparklineMark =
  | { kind: "line"; points: string }
  | { kind: "point"; cx: number; cy: number };

export type MacroPanelState = "current" | "stale" | "missing" | "insufficient";

export type MacroSeriesPanel = {
  sourceId: string;
  name: string;
  region: string;
  state: MacroPanelState;
  warning: string | null;
  valueLabel: string | null;
  valueUnit: string | null;
  periodLabel: string | null;
  changeLabel: string | null;
  measures: string | null;
  matters: string | null;
  sourceLabel: string | null;
  sourceHref: string | null;
  sourceLinkLabel: string | null;
  sourceLinkNote: string | null;
  freshnessLabel: string;
  gapLine: string | null;
  chartNote: string | null;
  details: readonly string[];
  evidenceHref: "/research" | null;
  chart: SeriesChartModel | null;
};

export type MacroConditionsView = {
  intro: string;
  freshnessRule: string;
  completenessLine: string;
  revisionLimit: string;
  groups: { id: string; label: string; panels: MacroSeriesPanel[] }[];
  unavailable: { id: string; name: string; detail: string }[];
};

const PERMANENT_OCTOBER_SOURCES = new Set([
  "bls_cps_unemployment_rate",
  "bls_cpi_u_all_items",
]);

const INTRO =
  "Each figure restates a stored live observation. A higher or lower value is not a judgement about the investment environment. There is no composite score.";

const MONTH = new Intl.DateTimeFormat("en-GB", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

const DAY = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
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

type Frequency = "monthly" | "weekly" | "quarterly";

export function presentMacroConditions(input: {
  series: readonly StoredSeriesWindow[];
  asOf: Date;
}): MacroConditionsView {
  const bySource = new Map(input.series.map((series) => [series.sourceId, series]));
  const groups: MacroConditionsView["groups"] = [];
  for (const spec of MACRO_SERIES) {
    let group = groups.find((item) => item.id === spec.groupId);
    if (!group) {
      group = { id: spec.groupId, label: spec.groupLabel, panels: [] };
      groups.push(group);
    }
    group.panels.push(presentSeries(spec, bySource.get(spec.sourceId), input.asOf));
  }
  const panels = groups.flatMap((group) => group.panels);
  return {
    intro: INTRO,
    freshnessRule: freshnessRule(input.asOf),
    completenessLine: completenessLine(panels),
    revisionLimit: revisionLimitLine(input.series),
    groups,
    unavailable: UNAVAILABLE_CONDITIONS.map((item) => ({ ...item })),
  };
}

export function subtractDecimal(later: string, earlier: string): string | null {
  const left = toScaled(later);
  const right = toScaled(earlier);
  if (!left || !right) return null;
  const scale = Math.max(left.scale, right.scale);
  const leftInt = left.int * 10n ** BigInt(scale - left.scale);
  const rightInt = right.int * 10n ** BigInt(scale - right.scale);
  return formatScaled(leftInt - rightInt, scale);
}

export function seriesState(
  frequency: string,
  latestPeriod: string | null,
  count: number,
  asOf: Date,
): MacroPanelState {
  if (count <= 0 || !latestPeriod) return "missing";
  if (count < 2) return "insufficient";
  if (isKnownFrequency(frequency) && isStale(frequency, latestPeriod, asOf)) return "stale";
  return "current";
}

export function isStale(frequency: Frequency, latestPeriod: string, asOf: Date): boolean {
  const today = asOf.toISOString().slice(0, 10);
  if (frequency === "monthly") {
    return latestPeriod < addMonths(monthStart(today), -MONTHLY_STALE_MONTHS);
  }
  if (frequency === "weekly") {
    return latestPeriod < addDays(today, -WEEKLY_STALE_DAYS);
  }
  return latestPeriod < addMonths(quarterStart(today), -(QUARTERLY_STALE_QUARTERS * 3));
}

export function gapsInWindow(periods: readonly string[], frequency: string): string[] {
  if (!isKnownFrequency(frequency)) return [];
  const sorted = [...periods].sort();
  const gaps: string[] = [];
  for (let index = 0; index < sorted.length - 1; index += 1) {
    const nextPeriod = sorted[index + 1];
    if (!nextPeriod) continue;
    let cursor = stepPeriod(sorted[index] ?? "", frequency);
    let guard = 0;
    while (cursor && nextPeriod && cursor < nextPeriod && guard < 36) {
      gaps.push(cursor);
      const next = stepPeriod(cursor, frequency);
      if (!next || next <= cursor) break;
      cursor = next;
      guard += 1;
    }
  }
  return gaps;
}

export function frequencySparkline(
  points: readonly { period: string; value: number }[],
  frequency: string,
): SparklineMark[] {
  if (!isKnownFrequency(frequency) || points.length < 2) return [];
  const sorted = [...points].sort((left, right) => left.period.localeCompare(right.period));
  const start = sorted[0]?.period;
  const end = sorted[sorted.length - 1]?.period;
  if (!start || !end) return [];
  const spanDays = Math.max(1, daysBetween(start, end));
  const values = sorted.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const plotWidth = 320 - 8 * 2;
  const plotHeight = 72 - 8 * 2;
  const placed = sorted.map((point) => ({
    period: point.period,
    x: 8 + (daysBetween(start, point.period) / spanDays) * plotWidth,
    y: 72 - 8 - ((point.value - min) / span) * plotHeight,
  }));
  const marks: SparklineMark[] = [];
  let run: typeof placed = [];
  const flush = () => {
    if (run.length === 1) {
      const only = run[0];
      if (only) marks.push({ kind: "point", cx: roundCoord(only.x), cy: roundCoord(only.y) });
    } else if (run.length > 1) {
      marks.push({
        kind: "line",
        points: run.map((point) => `${roundCoord(point.x)},${roundCoord(point.y)}`).join(" "),
      });
    }
    run = [];
  };
  for (let index = 0; index < placed.length; index += 1) {
    const current = placed[index];
    const previous = placed[index - 1];
    if (current && previous && !periodsAreAdjacent(previous.period, current.period, frequency)) flush();
    if (current) run.push(current);
  }
  flush();
  return marks;
}

export function revisionLimitLine(series: readonly StoredSeriesWindow[]): string {
  const stored = series.filter((item) => item.observations.length > 0);
  if (stored.length === 0) {
    return "No live series is stored, so no revision basis is shown. A historical date is not shown.";
  }
  if (stored.some((item) => !item.seriesProvenance)) {
    return "Revision basis is not stored for every series with observations. A historical date is not shown.";
  }
  if (stored.every((item) => item.seriesProvenance === "latest_revised")) {
    return "These stored series are latest revised. This view does not exclude a later revision. A latest-revised row is not a historical vintage.";
  }
  return "Revision basis is not only latest revised. A historical date is not shown on this page.";
}

function presentSeries(
  spec: (typeof MACRO_SERIES)[number],
  stored: StoredSeriesWindow | undefined,
  asOf: Date,
): MacroSeriesPanel {
  const meta = indicatorMetadata(spec.sourceId);
  const window = windowOf(stored);
  const latest = window[window.length - 1] ?? null;
  const previous = window[window.length - 2] ?? null;
  const frequency = stored?.frequency ?? "";
  const unit = stored?.unit ?? "";
  const state = seriesState(frequency, latest?.period ?? null, window.length, asOf);
  const gaps = gapsInWindow(
    window.map((observation) => observation.period),
    frequency,
  );
  const trusted = !meta || unit === meta.expectedUnit || !latest;
  const countNoun = trusted ? meta?.countNoun : undefined;
  const latestLevel = latest ? levelFor(latest.rawValue, unit, trusted, countNoun) : null;
  const diff = latest && previous ? subtractDecimal(latest.rawValue, previous.rawValue) : null;
  const chartPoints = window.flatMap((observation) => {
    const level = levelFor(observation.rawValue, unit, trusted, countNoun);
    if (!level) return [];
    return [
      {
        period: observation.period,
        display: level,
        dateLabel: formatPeriod(observation.period, frequency),
        valueLabel: pointLabel(level),
      },
    ];
  });
  const chart =
    latest && isKnownFrequency(frequency)
      ? buildSeriesChart({
          label: spec.name,
          caption: chartCaption(window, frequency),
          frequency,
          points: chartPoints,
        })
      : null;
  return {
    sourceId: spec.sourceId,
    name: spec.name,
    region: meta?.region ?? "",
    state,
    warning: warningLine(state, frequency, latest, meta),
    valueLabel: latestLevel?.headline ?? null,
    valueUnit: latestLevel?.beside ?? null,
    periodLabel: latest ? formatPeriod(latest.period, frequency) : null,
    changeLabel: changeLabel(diff, unit, trusted, previous, latest, frequency, countNoun),
    measures: measuresCopy(meta, stored),
    matters: meta?.matters ?? null,
    sourceLabel: meta ? `${meta.organisation} · ${meta.datasetLabel}` : null,
    sourceHref: meta?.sourceHref ?? null,
    sourceLinkLabel: meta ? linkLabel(meta) : null,
    sourceLinkNote: meta?.linkKind === "data_file" ? SERIES_PAGE_UNAVAILABLE : null,
    freshnessLabel: freshnessLine(stored?.retrievedAt ?? null, state),
    gapLine: gapCopy(spec.sourceId, gaps, frequency),
    chartNote: chart ? null : chartNote(state, frequency),
    details: technicalDetails(stored, window, latest, previous, diff, trusted, meta),
    evidenceHref: state === "missing" ? null : "/research",
    chart,
  };
}

function levelFor(
  raw: string,
  unit: string,
  trusted: boolean,
  countNoun?: "jobs" | "openings",
): DisplayLevel | null {
  if (!trusted) {
    const chartValue = Number(raw);
    if (!Number.isFinite(chartValue)) return null;
    return {
      headline: raw,
      precise: raw,
      chartValue,
      axisUnit: storedUnitPhrase(unit),
      tickSuffix: "",
      beside: storedUnitPhrase(unit),
      rescaled: false,
    };
  }
  return displayLevel(raw, unit, countNoun);
}

function pointLabel(level: DisplayLevel): string {
  return level.beside ? `${level.precise} ${level.beside}` : level.precise;
}

function changeLabel(
  diff: string | null,
  unit: string,
  trusted: boolean,
  previous: StoredObservation | null,
  latest: StoredObservation | null,
  frequency: string,
  countNoun?: "jobs" | "openings",
): string | null {
  if (!latest) return null;
  if (!previous) return "A previous observation is not stored, so no change is shown.";
  if (diff === null) return "The stored values are not numbers, so no change is shown.";
  const phrase = trusted ? displayChange(diff, unit, countNoun) : plainChange(diff, unit);
  if (!phrase) return "The stored values are not numbers, so no change is shown.";
  const adjacent = isKnownFrequency(frequency) && periodsAreAdjacent(previous.period, latest.period, frequency);
  return `${phrase} ${sinceText(previous.period, frequency, adjacent)}`;
}

function plainChange(diff: string, unit: string): string {
  if (/^-?0+(\.0+)?$/.test(diff)) return "Unchanged";
  const shown = diff.startsWith("-") ? diff : `+${diff}`;
  return `${shown} ${storedUnitPhrase(unit)}`;
}

function measuresCopy(meta: IndicatorMetadata | undefined, stored: StoredSeriesWindow | undefined): string | null {
  if (!meta) return null;
  if (!stored) return meta.measures;
  return `${meta.measures} ${seasonalSentence(stored.seasonalAdjustment)}`;
}

function warningLine(
  state: MacroPanelState,
  frequency: string,
  latest: StoredObservation | null,
  meta: IndicatorMetadata | undefined,
): string | null {
  if (state === "missing") return "No observation is stored.";
  if (state === "insufficient") {
    return "Only one observation is stored, so no change and no trend is shown.";
  }
  if (state === "stale" && latest) {
    const when = formatPeriod(latest.period, frequency);
    const subject = meta?.region === "Euro area" ? "current euro-area conditions" : "current conditions";
    return `Stale: ${when}. This is older than the lag allowed for a ${frequency} series, so it does not describe ${subject}.`;
  }
  return null;
}

function technicalDetails(
  stored: StoredSeriesWindow | undefined,
  window: readonly StoredObservation[],
  latest: StoredObservation | null,
  previous: StoredObservation | null,
  diff: string | null,
  trusted: boolean,
  meta: IndicatorMetadata | undefined,
): string[] {
  if (!stored || !latest) {
    return meta ? [`Source id: ${meta.sourceId}.`, "No retrieval is stored."] : ["No retrieval is stored."];
  }
  const lines = [
    `Stored value: ${latest.rawValue} ${storedUnitPhrase(stored.unit)}.`,
    seasonalSentence(stored.seasonalAdjustment),
    `${sentence(stored.frequency)}.`,
    provenanceSentence(stored.seriesProvenance),
    `Source id: ${stored.sourceId}.`,
    `Dataset: ${stored.datasetId}.`,
  ];
  if (!trusted) {
    lines.push("Stored unit does not match the indicator register, so the figure is not rescaled.");
  }
  if (previous && diff) {
    lines.push(
      `Stored difference from ${formatPeriod(previous.period, stored.frequency)}: ${diff} ${storedUnitPhrase(stored.unit)}.`,
    );
  }
  if (meta?.retrievalHref) lines.push(`Retrieval file: ${meta.retrievalHref}`);
  const windowLine = windowCopy(window, stored.frequency);
  if (windowLine) lines.push(windowLine);
  return lines;
}

function linkLabel(meta: IndicatorMetadata): string {
  if (meta.linkKind === "data_file") return "Official data file";
  if (meta.linkKind === "publication") return "Official release";
  return "Official series";
}

function seasonalSentence(value: string): string {
  if (value === "seasonally_adjusted") return "The stored series is seasonally adjusted.";
  if (value === "not_seasonally_adjusted") return "The stored series is not seasonally adjusted.";
  if (value === "unknown") return "Seasonal adjustment is not stated for the stored series.";
  return `Seasonal adjustment: ${value.replaceAll("_", " ")}.`;
}

function provenanceSentence(value: string | null): string {
  if (value === "latest_revised") {
    return "Latest revised. This is the current revised series, not a historical vintage.";
  }
  if (!value) return "Revision basis is not stored for this series.";
  return `Revision basis: ${value.replaceAll("_", " ")}. A historical date is not shown.`;
}

function completenessLine(panels: readonly MacroSeriesPanel[]): string {
  const stored = panels.filter((panel) => panel.state !== "missing").length;
  const missing = panels.filter((panel) => panel.state === "missing").length;
  const stale = panels.filter((panel) => panel.state === "stale").length;
  const insufficient = panels.filter((panel) => panel.state === "insufficient").length;
  const storedVerb = stored === 1 ? "has" : "have";
  const parts = [`${stored} of ${panels.length} tracked series ${storedVerb} a stored observation.`];
  if (missing > 0) parts.push(`${missing} ${missing === 1 ? "has" : "have"} no live observation.`);
  if (stale > 0) {
    parts.push(`${stale} ${stale === 1 ? "is" : "are"} stale for ${stale === 1 ? "its" : "their"} frequency.`);
  }
  if (insufficient > 0) {
    parts.push(`${insufficient} ${insufficient === 1 ? "is" : "are"} insufficient for a change and a trend.`);
  }
  parts.push("Liquidity and monetary-policy stance are not available.");
  return parts.join(" ");
}

function freshnessRule(asOf: Date): string {
  return [
    `A monthly series is stale when the latest period starts earlier than the first day of the month ${MONTHLY_STALE_MONTHS} months before the current month.`,
    `A weekly series is stale when the latest period starts more than ${WEEKLY_STALE_DAYS} days before today.`,
    `A quarterly series is stale when the latest period starts earlier than the first day of the quarter ${QUARTERLY_STALE_QUARTERS} quarters before the current quarter.`,
    `Comparison date: ${DAY.format(asOf)} UTC.`,
  ].join(" ");
}

function freshnessLine(retrievedAt: string | null, state: MacroPanelState): string {
  if (state === "missing") return "No retrieval is stored.";
  if (!retrievedAt) return "Retrieval time is not stored.";
  const date = new Date(retrievedAt);
  if (Number.isNaN(date.getTime())) return "Retrieval time is not stored.";
  return `Retrieved ${RETRIEVED.format(date)} UTC.`;
}

function windowOf(stored: StoredSeriesWindow | undefined): StoredObservation[] {
  if (!stored) return [];
  const byPeriod = new Map<string, StoredObservation>();
  for (const observation of stored.observations) {
    const period = observation.period.slice(0, 10);
    const rawValue = observation.rawValue.trim();
    if (!period || !rawValue) continue;
    byPeriod.set(period, { period, rawValue });
  }
  return [...byPeriod.values()]
    .sort((left, right) => left.period.localeCompare(right.period))
    .slice(-MACRO_CONDITIONS_WINDOW);
}

function windowCopy(window: readonly StoredObservation[], frequency: string): string {
  const first = window[0];
  const last = window[window.length - 1];
  if (!first || !last) return "";
  const freq = isKnownFrequency(frequency) ? frequency : "stored";
  const from = formatPeriod(first.period, frequency);
  const to = formatPeriod(last.period, frequency);
  const span = first.period === last.period ? from : `from ${from} to ${to}`;
  const noun = window.length === 1 ? "observation" : "observations";
  return `This window is the latest ${window.length} stored ${freq} ${noun}, ${span}. Earlier observations are not loaded. The limit is ${MACRO_CONDITIONS_WINDOW}.`;
}

function chartCaption(window: readonly StoredObservation[], frequency: string): string {
  const first = window[0];
  const last = window[window.length - 1];
  if (!first || !last) return "";
  if (first.period === last.period) return formatPeriod(first.period, frequency);
  return `${formatPeriod(first.period, frequency)} to ${formatPeriod(last.period, frequency)}`;
}

function gapCopy(sourceId: string, gaps: readonly string[], frequency: string): string | null {
  if (gaps.length === 0) return null;
  const october = gaps.filter((gap) => gap.slice(0, 7) === "2025-10");
  const other = gaps.filter((gap) => gap.slice(0, 7) !== "2025-10");
  const parts: string[] = [];
  if (october.length > 0 && PERMANENT_OCTOBER_SOURCES.has(sourceId)) {
    parts.push("Permanently missing: October 2025. The Bureau of Labor Statistics did not publish this month.");
  } else if (october.length > 0) {
    other.unshift(...october);
  }
  if (other.length > 0) {
    parts.push(`Not stored in this window: ${other.map((gap) => formatPeriod(gap, frequency)).join(", ")}.`);
  }
  parts.push("The line is not drawn across a missing period. Nothing was filled in.");
  return parts.join(" ");
}

function chartNote(state: MacroPanelState, frequency: string): string | null {
  if (state === "missing" || state === "insufficient") return null;
  if (!isKnownFrequency(frequency)) {
    return "This frequency is not monthly, weekly, or quarterly, so no line is drawn.";
  }
  return null;
}

function sinceText(period: string, frequency: string, adjacent: boolean): string {
  const label = formatPeriod(period, frequency);
  const when = frequency === "monthly" ? label : `the ${label}`;
  if (adjacent) return `since ${when}`;
  return `since ${when}, the previous stored observation`;
}

function formatPeriod(iso: string, frequency: string): string {
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return iso;
  if (frequency === "weekly") return `week of ${DAY.format(date)}`;
  if (frequency === "quarterly") return `quarter starting ${DAY.format(date)}`;
  return MONTH.format(date);
}

function sentence(value: string): string {
  if (value.length === 0) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function isKnownFrequency(frequency: string): frequency is Frequency {
  return frequency === "monthly" || frequency === "weekly" || frequency === "quarterly";
}

function stepPeriod(iso: string, frequency: string): string | null {
  if (frequency === "monthly") return addMonths(iso, 1);
  if (frequency === "quarterly") return addMonths(iso, 3);
  if (frequency === "weekly") return addDays(iso, 7);
  return null;
}

function monthStart(iso: string): string {
  return `${iso.slice(0, 7)}-01`;
}

function quarterStart(iso: string): string {
  const month = Number(iso.slice(5, 7));
  const quarterMonth = Math.floor((month - 1) / 3) * 3 + 1;
  return `${iso.slice(0, 4)}-${String(quarterMonth).padStart(2, "0")}-01`;
}

function addMonths(iso: string, months: number): string {
  const [yearText, monthText, dayText] = iso.slice(0, 10).split("-");
  const date = new Date(Date.UTC(Number(yearText), Number(monthText) - 1 + months, Number(dayText)));
  return date.toISOString().slice(0, 10);
}

function addDays(iso: string, days: number): string {
  const [yearText, monthText, dayText] = iso.slice(0, 10).split("-");
  const date = new Date(Date.UTC(Number(yearText), Number(monthText) - 1, Number(dayText) + days));
  return date.toISOString().slice(0, 10);
}

function daysBetween(start: string, end: string): number {
  const ms = Date.parse(`${end.slice(0, 10)}T00:00:00Z`) - Date.parse(`${start.slice(0, 10)}T00:00:00Z`);
  return Math.round(ms / 86_400_000);
}

function roundCoord(value: number): number {
  return Math.round(value * 100) / 100;
}

function toScaled(value: string): { int: bigint; scale: number } | null {
  const trimmed = value.trim();
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) return null;
  const negative = trimmed.startsWith("-");
  const body = negative ? trimmed.slice(1) : trimmed;
  const [whole, frac = ""] = body.split(".");
  const digits = `${whole}${frac}`.replace(/^0+(?=\d)/, "");
  return { int: BigInt(digits || "0") * (negative ? -1n : 1n), scale: frac.length };
}

function formatScaled(value: bigint, scale: number): string {
  const negative = value < 0n;
  const abs = negative ? -value : value;
  if (abs === 0n) return "0";
  const text = abs.toString().padStart(scale + 1, "0");
  if (scale === 0) return negative ? `-${text}` : text;
  const whole = text.slice(0, -scale);
  const frac = text.slice(-scale).replace(/0+$/, "");
  const body = frac ? `${whole}.${frac}` : whole;
  return negative ? `-${body}` : body;
}
