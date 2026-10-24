import type { DisplayLevel } from "./format-indicator.ts";

export const SERIES_CHART_WIDTH = 360;
export const SERIES_CHART_HEIGHT = 168;

const PADDING_LEFT = 52;
const PADDING_RIGHT = 12;
const PADDING_TOP = 8;
const PADDING_BOTTOM = 32;

export type ChartObservation = {
  period: string;
  x: number;
  y: number;
  dateLabel: string;
  valueLabel: string;
};

export type ChartTick = {
  x?: number;
  y?: number;
  label: string;
  value: number;
};

export type SeriesChartModel = {
  label: string;
  caption: string;
  unitLabel: string;
  width: number;
  height: number;
  plot: { x: number; y: number; width: number; height: number };
  yTicks: { y: number; label: string; value: number }[];
  xTicks: { x: number; label: string; anchor: "start" | "middle" | "end" }[];
  segments: { periods: string[]; d: string }[];
  points: ChartObservation[];
};

type InputPoint = {
  period: string;
  display: DisplayLevel;
  dateLabel: string;
  valueLabel: string;
};

const SHORT_MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function buildSeriesChart(input: {
  label: string;
  caption: string;
  frequency: string;
  points: readonly InputPoint[];
}): SeriesChartModel | null {
  if (!isKnownFrequency(input.frequency) || input.points.length < 2) return null;
  const sorted = [...input.points].sort((left, right) => left.period.localeCompare(right.period));
  const start = sorted[0]?.period;
  const end = sorted[sorted.length - 1]?.period;
  if (!start || !end || start === end) return null;
  const values = sorted.map((point) => point.display.chartValue);
  const yAxis = axisTicks(values);
  if (!yAxis) return null;
  const spanDays = Math.max(1, daysBetween(start, end));
  const plot = {
    x: PADDING_LEFT,
    y: PADDING_TOP,
    width: SERIES_CHART_WIDTH - PADDING_LEFT - PADDING_RIGHT,
    height: SERIES_CHART_HEIGHT - PADDING_TOP - PADDING_BOTTOM,
  };
  const placed: ChartObservation[] = sorted.map((point) => ({
    period: point.period,
    x: roundCoord(plot.x + (daysBetween(start, point.period) / spanDays) * plot.width),
    y: roundCoord(
      plot.y + ((yAxis.max - point.display.chartValue) / (yAxis.max - yAxis.min)) * plot.height,
    ),
    dateLabel: point.dateLabel,
    valueLabel: point.valueLabel,
  }));
  const suffix = sorted[0]?.display.tickSuffix ?? "";
  const decimals = decimalsForStep(yAxis.step);
  return {
    label: input.label,
    caption: input.caption,
    unitLabel: sorted[0]?.display.axisUnit ?? "",
    width: SERIES_CHART_WIDTH,
    height: SERIES_CHART_HEIGHT,
    plot,
    yTicks: yAxis.ticks.map((value) => ({
      value,
      y: roundCoord(plot.y + ((yAxis.max - value) / (yAxis.max - yAxis.min)) * plot.height),
      label: `${value.toFixed(decimals)}${suffix}`,
    })),
    xTicks: xTicks(placed, input.frequency),
    segments: lineSegments(placed, input.frequency),
    points: placed,
  };
}

export function axisTicks(values: readonly number[]): { min: number; max: number; step: number; ticks: number[] } | null {
  if (values.length === 0 || values.some((value) => !Number.isFinite(value))) return null;
  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
  const span = dataMax - dataMin;
  const step = span === 0 ? niceStep(Math.max(Math.abs(dataMin) * 0.05, 0.1)) : niceStep(span);
  if (!(step > 0)) return null;
  let min = Math.floor(dataMin / step + 1e-9) * step;
  let max = Math.ceil(dataMax / step - 1e-9) * step;
  if (min === max) {
    min -= step;
    max += step;
  }
  if (dataMin - min < step * 0.2) min -= step;
  if (max - dataMax < step * 0.2) max += step;
  const count = Math.round((max - min) / step);
  const ticks: number[] = [];
  for (let index = 0; index <= count && index < 8; index += 1) {
    ticks.push(Number((min + index * step).toFixed(6)));
  }
  if (ticks.length < 2) return null;
  return { min: ticks[0] ?? min, max: ticks[ticks.length - 1] ?? max, step, ticks };
}

export function periodsAreAdjacent(previous: string, next: string, frequency: string): boolean {
  return stepPeriod(previous, frequency) === next;
}

function lineSegments(points: readonly ChartObservation[], frequency: string): { periods: string[]; d: string }[] {
  const segments: { periods: string[]; d: string }[] = [];
  let run: ChartObservation[] = [];
  const flush = () => {
    if (run.length > 1) {
      segments.push({
        periods: run.map((point) => point.period),
        d: smoothLinePath(run),
      });
    }
    run = [];
  };
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const previous = points[index - 1];
    if (current && previous && !periodsAreAdjacent(previous.period, current.period, frequency)) flush();
    if (current) run.push(current);
  }
  flush();
  return segments;
}

function xTicks(
  points: readonly ChartObservation[],
  frequency: string,
): { x: number; label: string; anchor: "start" | "middle" | "end" }[] {
  const indexes = tickIndexes(points.length);
  const chosen: number[] = [];
  for (const index of indexes) {
    const point = points[index];
    const previous = points[chosen[chosen.length - 1] ?? -1];
    if (!point) continue;
    if (previous && Math.abs(point.x - previous.x) < 68 && index !== points.length - 1) continue;
    if (previous && index === points.length - 1 && Math.abs(point.x - previous.x) < 68) {
      chosen.pop();
    }
    chosen.push(index);
  }
  const spanYears = new Set(points.map((point) => point.period.slice(0, 4))).size > 1;
  return chosen.map((index, position) => {
    const point = points[index];
    if (!point) return { x: 0, label: "", anchor: "middle" as const };
    const anchor = position === 0 ? "start" : position === chosen.length - 1 ? "end" : "middle";
    return { x: point.x, label: tickLabel(point.period, frequency, spanYears || position === 0), anchor };
  });
}

function tickLabel(period: string, frequency: string, includeYear: boolean): string {
  if (frequency === "quarterly") {
    const month = Number(period.slice(5, 7));
    const quarter = Math.floor((month - 1) / 3) + 1;
    return `Q${quarter} ${period.slice(0, 4)}`;
  }
  const month = SHORT_MONTH[Number(period.slice(5, 7)) - 1] ?? "";
  if (frequency === "weekly") {
    const day = Number(period.slice(8, 10));
    return includeYear ? `${day} ${month} ${period.slice(0, 4)}` : `${day} ${month}`;
  }
  return `${month} ${period.slice(0, 4)}`;
}

function tickIndexes(count: number): number[] {
  if (count <= 3) return Array.from({ length: count }, (_, index) => index);
  const mid1 = Math.round((count - 1) / 3);
  const mid2 = Math.round((2 * (count - 1)) / 3);
  return [...new Set([0, mid1, mid2, count - 1])].sort((left, right) => left - right);
}

function niceStep(span: number): number {
  if (!(span > 0)) return 1;
  const target = span / 3;
  const power = 10 ** Math.floor(Math.log10(target));
  const fraction = target / power;
  const nice = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 2.5 ? 2.5 : fraction <= 5 ? 5 : 10;
  return nice * power;
}

function decimalsForStep(step: number): number {
  if (!(step > 0)) return 0;
  for (let decimals = 0; decimals <= 6; decimals += 1) {
    const shown = Number(step.toFixed(decimals));
    if (shown > 0 && Math.abs(shown - step) <= step * 0.001) return decimals;
  }
  return 6;
}

function isKnownFrequency(frequency: string): boolean {
  return frequency === "monthly" || frequency === "weekly" || frequency === "quarterly";
}

function stepPeriod(iso: string, frequency: string): string | null {
  if (frequency === "monthly") return addMonths(iso, 1);
  if (frequency === "quarterly") return addMonths(iso, 3);
  if (frequency === "weekly") return addDays(iso, 7);
  return null;
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

function smoothLinePath(points: readonly { x: number; y: number }[]): string {
  const first = points[0];
  if (!first) return "";
  if (points.length === 1) return `M ${formatCoord(first.x)} ${formatCoord(first.y)}`;
  const slopes: number[] = [];
  const spans: number[] = [];
  for (let index = 0; index < points.length - 1; index += 1) {
    const left = points[index];
    const right = points[index + 1];
    if (!left || !right) continue;
    const span = right.x - left.x;
    spans.push(span);
    slopes.push(span === 0 ? 0 : (right.y - left.y) / span);
  }
  const tangents = slopes.map((slope, index) => {
    if (index === 0) return slope;
    const previous = slopes[index - 1] ?? 0;
    return previous * slope <= 0 ? 0 : (previous + slope) / 2;
  });
  tangents.push(slopes[slopes.length - 1] ?? 0);
  const commands = [`M ${formatCoord(first.x)} ${formatCoord(first.y)}`];
  for (let index = 0; index < points.length - 1; index += 1) {
    const left = points[index];
    const right = points[index + 1];
    const span = spans[index] ?? 0;
    if (!left || !right) continue;
    let start = tangents[index] ?? 0;
    let end = tangents[index + 1] ?? 0;
    const secant = slopes[index] ?? 0;
    if (secant === 0) {
      start = 0;
      end = 0;
    } else {
      const alpha = start / secant;
      const beta = end / secant;
      const magnitude = alpha * alpha + beta * beta;
      if (magnitude > 9) {
        const scale = 3 / Math.sqrt(magnitude);
        start = scale * alpha * secant;
        end = scale * beta * secant;
      }
    }
    commands.push(
      `C ${formatCoord(left.x + span / 3)} ${formatCoord(left.y + (start * span) / 3)} ${formatCoord(right.x - span / 3)} ${formatCoord(right.y - (end * span) / 3)} ${formatCoord(right.x)} ${formatCoord(right.y)}`,
    );
  }
  return commands.join(" ");
}

function formatCoord(value: number): string {
  return (Math.round(value * 100) / 100).toString();
}
