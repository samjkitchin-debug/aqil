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

export type SparklineMark =
  | { kind: "line"; points: string }
  | { kind: "point"; cx: number; cy: number };

export type MacroPanelState = "current" | "stale" | "missing" | "insufficient";

export type MacroSeriesPanel = {
  sourceId: string;
  name: string;
  state: MacroPanelState;
  stateLine: string;
  detailLine: string | null;
  sourceLine: string | null;
  description: string;
  windowLine: string | null;
  gapLine: string | null;
  chartNote: string | null;
  freshnessLine: string;
  evidenceHref: "/research" | null;
  chart: {
    label: string;
    caption: string;
    width: number;
    height: number;
    marks: SparklineMark[];
  } | null;
};

export type MacroConditionsView = {
  intro: string;
  freshnessRule: string;
  completenessLine: string;
  groups: { id: string; label: string; panels: MacroSeriesPanel[] }[];
  unavailable: { id: string; name: string; detail: string }[];
};

export const MACRO_SPARKLINE_WIDTH = 320;
export const MACRO_SPARKLINE_HEIGHT = 72;

const SPARKLINE_PADDING = 8;
const CHART_INSUFFICIENT_COPY = "Chart unavailable — insufficient observation points.";
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
  const plotWidth = MACRO_SPARKLINE_WIDTH - SPARKLINE_PADDING * 2;
  const plotHeight = MACRO_SPARKLINE_HEIGHT - SPARKLINE_PADDING * 2;
  const placed = sorted.map((point) => ({
    period: point.period,
    x: SPARKLINE_PADDING + (daysBetween(start, point.period) / spanDays) * plotWidth,
    y:
      MACRO_SPARKLINE_HEIGHT -
      SPARKLINE_PADDING -
      ((point.value - min) / span) * plotHeight,
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
    if (current && previous && !isAdjacent(previous.period, current.period, frequency)) flush();
    if (current) run.push(current);
  }
  flush();
  return marks;
}

function presentSeries(
  spec: (typeof MACRO_SERIES)[number],
  stored: StoredSeriesWindow | undefined,
  asOf: Date,
): MacroSeriesPanel {
  const window = windowOf(stored);
  const latest = window[window.length - 1] ?? null;
  const frequency = stored?.frequency ?? "";
  const state = seriesState(frequency, latest?.period ?? null, window.length, asOf);
  const gaps = gapsInWindow(
    window.map((observation) => observation.period),
    frequency,
  );
  const windowLine = latest ? windowCopy(window, frequency) : null;
  const gapLine = gapCopy(spec.sourceId, gaps, frequency);
  const numericPoints = window.flatMap((observation) => {
    const value = numericValue(observation.rawValue);
    return value === null ? [] : [{ period: observation.period, value }];
  });
  const marks = frequencySparkline(numericPoints, frequency);
  const chart =
    marks.length > 0 && windowLine
      ? {
          label: spec.name,
          caption: windowLine,
          width: MACRO_SPARKLINE_WIDTH,
          height: MACRO_SPARKLINE_HEIGHT,
          marks,
        }
      : null;
  return {
    sourceId: spec.sourceId,
    name: spec.name,
    state,
    stateLine: stateLine(state, frequency, latest, asOf),
    detailLine: stored && latest ? detailLine(stored) : null,
    sourceLine: stored && latest ? `Source ${stored.sourceId}. Dataset ${stored.datasetId}.` : null,
    description: description(window, stored?.unit ?? "", frequency),
    windowLine: chart ? null : windowLine,
    gapLine,
    chartNote: chartNote(state, frequency, chart !== null),
    freshnessLine: freshnessLine(stored?.retrievedAt ?? null, state),
    evidenceHref: state === "missing" ? null : "/research",
    chart,
  };
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

function description(
  window: readonly StoredObservation[],
  unit: string,
  frequency: string,
): string {
  const latest = window[window.length - 1];
  if (!latest) return "No live observation is stored for this series.";
  const latestSentence = `Latest observation: ${latest.rawValue} ${unitLabel(unit)} for ${formatPeriod(latest.period, frequency)}.`;
  const previous = window[window.length - 2];
  if (!previous) {
    return `${latestSentence} A previous stored observation is not available, so no difference is stated.`;
  }
  const previousLabel = formatPeriod(previous.period, frequency);
  const diff = subtractDecimal(latest.rawValue, previous.rawValue);
  if (diff === null) {
    return `${latestSentence} Previous stored observation: ${previous.rawValue} ${unitLabel(unit)} for ${previousLabel}. The stored values are not numbers, so no difference is stated.`;
  }
  return `${latestSentence} Previous stored observation: ${previous.rawValue} ${unitLabel(unit)} for ${previousLabel}. Difference: ${diffPhrase(diff, unit)}.`;
}

function completenessLine(panels: readonly MacroSeriesPanel[]): string {
  const stored = panels.filter((panel) => panel.state !== "missing").length;
  const missing = panels.filter((panel) => panel.state === "missing").length;
  const stale = panels.filter((panel) => panel.state === "stale").length;
  const insufficient = panels.filter((panel) => panel.state === "insufficient").length;
  const storedVerb = stored === 1 ? "has" : "have";
  const parts = [
    `${stored} of ${panels.length} tracked series ${storedVerb} a stored observation.`,
  ];
  if (missing > 0) {
    parts.push(
      `${missing} ${missing === 1 ? "has" : "have"} no live observation.`,
    );
  }
  if (stale > 0) {
    parts.push(
      `${stale} ${stale === 1 ? "is" : "are"} stale for ${stale === 1 ? "its" : "their"} frequency.`,
    );
  }
  if (insufficient > 0) {
    parts.push(
      `${insufficient} ${insufficient === 1 ? "is" : "are"} insufficient for a change and a trend.`,
    );
  }
  parts.push("Liquidity and monetary-policy stance are not available.");
  return parts.join(" ");
}

function freshnessRule(asOf: Date): string {
  return [
    `A monthly series is stale when the latest period starts earlier than the first day of the month ${MONTHLY_STALE_MONTHS} months before the current month.`,
    `A weekly series is stale when the latest period starts more than ${WEEKLY_STALE_DAYS} days before today.`,
    `A quarterly series is stale when the latest period starts earlier than the first day of the quarter ${QUARTERLY_STALE_QUARTERS} quarters before the current quarter.`,
    `Comparison date: ${formatAsOf(asOf)} UTC.`,
  ].join(" ");
}

function stateLine(
  state: MacroPanelState,
  frequency: string,
  latest: StoredObservation | null,
  asOf: Date,
): string {
  if (state === "missing") return "Data state: missing.";
  if (state === "insufficient") {
    const stale =
      latest && isKnownFrequency(frequency) && isStale(frequency, latest.period, asOf);
    const base =
      "Data state: insufficient. Fewer than two stored observations are available for a change and a trend.";
    return stale
      ? `${base} The latest period is also older than the lag allowed for a ${frequency} series.`
      : base;
  }
  if (state === "stale") {
    return `Data state: stale. The latest period is older than the lag allowed for a ${frequency} series.`;
  }
  return "Data state: current.";
}

function freshnessLine(retrievedAt: string | null, state: MacroPanelState): string {
  if (state === "missing") return "No retrieval is stored.";
  if (!retrievedAt) return "Retrieval time is not stored.";
  const date = new Date(retrievedAt);
  if (Number.isNaN(date.getTime())) return "Retrieval time is not stored.";
  return `Retrieved ${RETRIEVED.format(date)} UTC.`;
}

function detailLine(series: StoredSeriesWindow): string {
  const parts = [
    `Stored unit ${series.unit}.`,
    `${sentence(seasonalPhrase(series.seasonalAdjustment))}.`,
    `${sentence(series.frequency)}.`,
  ];
  if (series.seriesProvenance) {
    parts.push(`${sentence(series.seriesProvenance.replaceAll("_", " "))}.`);
  }
  return parts.join(" ");
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

function gapCopy(sourceId: string, gaps: readonly string[], frequency: string): string | null {
  if (gaps.length === 0) return null;
  const october = gaps.filter((gap) => gap.slice(0, 7) === "2025-10");
  const other = gaps.filter((gap) => gap.slice(0, 7) !== "2025-10");
  const parts: string[] = [];
  if (october.length > 0 && PERMANENT_OCTOBER_SOURCES.has(sourceId)) {
    parts.push(
      "Permanently missing: October 2025. The Bureau of Labor Statistics did not publish this month.",
    );
  } else if (october.length > 0) {
    other.unshift(...october);
  }
  if (other.length > 0) {
    parts.push(`Not stored in this window: ${other.map((gap) => formatPeriod(gap, frequency)).join(", ")}.`);
  }
  parts.push("The line is not drawn across a missing period. Nothing was filled in.");
  return parts.join(" ");
}

function chartNote(
  state: MacroPanelState,
  frequency: string,
  hasChart: boolean,
): string | null {
  if (hasChart || state === "missing") return null;
  if (!isKnownFrequency(frequency) && state !== "insufficient") {
    return "This frequency is not monthly, weekly, or quarterly, so no line is drawn.";
  }
  return CHART_INSUFFICIENT_COPY;
}

function diffPhrase(diff: string, unit: string): string {
  if (diff === "0") return "unchanged";
  const lower = diff.startsWith("-");
  const magnitude = lower ? diff.slice(1) : diff;
  return `${magnitude} ${differenceUnit(unit)} ${lower ? "lower" : "higher"}`;
}

function differenceUnit(unit: string): string {
  if (unit === "percent" || unit === "percent_per_year" || unit === "percent_net_tightening") {
    return "percentage points";
  }
  return unitLabel(unit);
}

function unitLabel(unit: string): string {
  switch (unit) {
    case "percent":
      return "percent";
    case "thousands":
      return "thousands";
    case "usd_millions":
      return "millions of US dollars";
    case "percent_per_year":
      return "percent per year";
    case "percent_net_tightening":
      return "percent net tightening";
    case "index_2017_100":
      return "index, 2017 = 100";
    case "index, 2015 = 100":
      return "index, 2015 = 100";
    default:
      return unit;
  }
}

function seasonalPhrase(value: string): string {
  if (value === "seasonally_adjusted") return "seasonally adjusted";
  if (value === "not_seasonally_adjusted") return "not seasonally adjusted";
  if (value === "unknown") return "seasonal adjustment not stated";
  return value.replaceAll("_", " ");
}

function formatPeriod(iso: string, frequency: string): string {
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return iso;
  if (frequency === "weekly") return `week of ${DAY.format(date)}`;
  if (frequency === "quarterly") return `quarter starting ${DAY.format(date)}`;
  return MONTH.format(date);
}

function formatAsOf(asOf: Date): string {
  return DAY.format(asOf);
}

function sentence(value: string): string {
  if (value.length === 0) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function isKnownFrequency(frequency: string): frequency is Frequency {
  return frequency === "monthly" || frequency === "weekly" || frequency === "quarterly";
}

function isAdjacent(previous: string, next: string, frequency: string): boolean {
  return stepPeriod(previous, frequency) === next;
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
  const date = new Date(
    Date.UTC(Number(yearText), Number(monthText) - 1 + months, Number(dayText)),
  );
  return date.toISOString().slice(0, 10);
}

function addDays(iso: string, days: number): string {
  const [yearText, monthText, dayText] = iso.slice(0, 10).split("-");
  const date = new Date(Date.UTC(Number(yearText), Number(monthText) - 1, Number(dayText) + days));
  return date.toISOString().slice(0, 10);
}

function daysBetween(start: string, end: string): number {
  const ms =
    Date.parse(`${end.slice(0, 10)}T00:00:00Z`) - Date.parse(`${start.slice(0, 10)}T00:00:00Z`);
  return Math.round(ms / 86_400_000);
}

function roundCoord(value: number): number {
  return Math.round(value * 100) / 100;
}

function numericValue(raw: string): number | null {
  if (!/^-?\d+(\.\d+)?$/.test(raw.trim())) return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

function toScaled(value: string): { int: bigint; scale: number } | null {
  const trimmed = value.trim();
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) return null;
  const negative = trimmed.startsWith("-");
  const body = negative ? trimmed.slice(1) : trimmed;
  const [whole, frac = ""] = body.split(".");
  const digits = `${whole}${frac}`.replace(/^0+(?=\d)/, "");
  return { int: BigInt(digits) * (negative ? -1n : 1n), scale: frac.length };
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
