import { effectiveJournalEvents, type JournalEvent, type JournalReplay } from "./journal.ts";
import {
  explainMarketValue,
  ratesOn,
  toReporting,
  type SuppliedRate,
} from "./journal-valuation.ts";

export const XIRR_UNAVAILABLE = "Money-weighted return is unavailable because the cashflows cannot be solved.";
export const TWR_UNAVAILABLE = "Time-weighted return is unavailable without interim valuations.";

export type SolvedRate =
  | { status: "available"; rate: string; from: string; to: string }
  | { status: "unavailable"; reason: string };

type Flow = { occurredOn: string; amountMinor: bigint };

export function externalContributions(
  events: readonly JournalEvent[],
  rates: readonly SuppliedRate[],
  reportingCurrency: string,
  asOf: string,
): { status: "available"; flows: Flow[] } | { status: "unavailable" } {
  const flows: Flow[] = [];
  for (const event of effectiveJournalEvents(events.filter((item) => item.occurredOn <= asOf))) {
    if (event.eventType !== "deposit" && event.eventType !== "withdrawal") continue;
    if (event.cashAmountMinor === null) return { status: "unavailable" };
    const fx = ratesOn(rates, event.occurredOn, reportingCurrency);
    const amount = toReporting(event.cashAmountMinor, event.currency, reportingCurrency, fx);
    if (amount === null) return { status: "unavailable" };
    flows.push({ occurredOn: event.occurredOn, amountMinor: amount });
  }
  return { status: "available", flows: mergeFlows(flows) };
}

export function moneyWeightedReturn(input: {
  contributions: readonly Flow[];
  terminal: { asOf: string; amountMinor: bigint } | null;
}): SolvedRate {
  if (!input.terminal) return unsolved();
  const investor: Flow[] = input.contributions.map((flow) => ({
    occurredOn: flow.occurredOn,
    amountMinor: -flow.amountMinor,
  }));
  if (input.terminal.amountMinor !== 0n) {
    investor.push({ occurredOn: input.terminal.asOf, amountMinor: input.terminal.amountMinor });
  }
  return solveXirr(investor);
}

export function solveXirr(flows: readonly Flow[]): SolvedRate {
  const merged = mergeFlows(flows).filter((flow) => flow.amountMinor !== 0n);
  if (merged.length < 2) return unsolved();
  let changes = 0;
  let previous = 0n;
  for (const flow of merged) {
    if (previous !== 0n && (previous < 0n) !== (flow.amountMinor < 0n)) changes += 1;
    previous = flow.amountMinor;
  }
  if (changes !== 1) return unsolved();
  const start = merged[0]?.occurredOn;
  const end = merged[merged.length - 1]?.occurredOn;
  if (!start || !end || start === end) return unsolved();
  const series: { t: number; amount: number }[] = [];
  for (const flow of merged) {
    if (flow.amountMinor > BigInt(Number.MAX_SAFE_INTEGER) || flow.amountMinor < -BigInt(Number.MAX_SAFE_INTEGER)) {
      return unsolved();
    }
    series.push({ t: yearFraction(start, flow.occurredOn), amount: Number(flow.amountMinor) });
  }
  const rate = findRate(series);
  if (rate === null) return unsolved();
  return { status: "available", rate: formatDecimalRate(rate), from: start, to: end };
}

export function timeWeightedReturn(input: {
  points: readonly { asOf: string; amountMinor: bigint }[];
  contributions: readonly Flow[];
  asOf: string;
}): SolvedRate {
  const points = [...input.points].sort((left, right) => left.asOf.localeCompare(right.asOf));
  while (points[0]?.amountMinor === 0n) points.shift();
  if (points.length < 2 || points[points.length - 1]?.asOf !== input.asOf) {
    return { status: "unavailable", reason: TWR_UNAVAILABLE };
  }
  const dates = new Set<string>();
  for (const point of points) {
    if (dates.has(point.asOf)) return { status: "unavailable", reason: TWR_UNAVAILABLE };
    dates.add(point.asOf);
  }
  for (const flow of input.contributions) {
    if (flow.amountMinor !== 0n && !dates.has(flow.occurredOn)) {
      return { status: "unavailable", reason: TWR_UNAVAILABLE };
    }
  }
  let numerator = 1n;
  let denominator = 1n;
  for (let index = 0; index < points.length - 1; index += 1) {
    const start = points[index];
    const end = points[index + 1];
    if (!start || !end || start.amountMinor <= 0n) {
      return { status: "unavailable", reason: TWR_UNAVAILABLE };
    }
    const flow = input.contributions
      .filter((item) => item.occurredOn === end.asOf)
      .reduce((sum, item) => sum + item.amountMinor, 0n);
    const growth = end.amountMinor - flow;
    if (growth < 0n) return { status: "unavailable", reason: TWR_UNAVAILABLE };
    numerator *= growth;
    denominator *= start.amountMinor;
  }
  if (denominator === 0n) return { status: "unavailable", reason: TWR_UNAVAILABLE };
  const first = points[0];
  const last = points[points.length - 1];
  if (!first || !last) return { status: "unavailable", reason: TWR_UNAVAILABLE };
  return {
    status: "available",
    rate: formatRatioMinusOne(numerator, denominator),
    from: first.asOf,
    to: last.asOf,
  };
}

export function portfolioTotal(replay: JournalReplay): { asOfReady: boolean; amountMinor: bigint; currency: string } | null {
  if (replay.marketValue.status !== "available" || replay.reportingCash.status !== "available") return null;
  if (replay.marketValue.currency !== replay.reportingCash.currency) return null;
  return {
    asOfReady: true,
    currency: replay.marketValue.currency,
    amountMinor: replay.marketValue.amountMinor + replay.reportingCash.amountMinor,
  };
}

export function valuedPoints(input: {
  events: readonly JournalEvent[];
  prices: Parameters<typeof explainMarketValue>[1];
  rates: readonly SuppliedRate[];
  reportingCurrency: string;
  asOf: string;
  contributions: readonly Flow[];
}): { status: "available"; points: { asOf: string; amountMinor: bigint }[] } | { status: "unavailable" } {
  const dates = new Set<string>([input.asOf]);
  for (const flow of input.contributions) dates.add(flow.occurredOn);
  for (const price of input.prices) {
    if (price.asOf <= input.asOf) dates.add(price.asOf);
  }
  const points: { asOf: string; amountMinor: bigint }[] = [];
  for (const date of [...dates].sort()) {
    const explained = explainMarketValue(input.events, input.prices, input.rates, input.reportingCurrency, date);
    const total = portfolioTotal(explained.replay);
    const required = date === input.asOf || input.contributions.some((flow) => flow.occurredOn === date);
    if (!total) {
      if (required) return { status: "unavailable" };
      continue;
    }
    points.push({ asOf: date, amountMinor: total.amountMinor });
  }
  return { status: "available", points };
}

function mergeFlows(flows: readonly Flow[]): Flow[] {
  const merged: Flow[] = [];
  for (const flow of [...flows].sort((left, right) => left.occurredOn.localeCompare(right.occurredOn))) {
    const last = merged[merged.length - 1];
    if (last && last.occurredOn === flow.occurredOn) last.amountMinor += flow.amountMinor;
    else merged.push({ ...flow });
  }
  return merged;
}

function unsolved(): SolvedRate {
  return { status: "unavailable", reason: XIRR_UNAVAILABLE };
}

function yearFraction(start: string, date: string): number {
  const elapsed = Date.parse(`${date}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`);
  return elapsed / 86_400_000 / 365;
}

function findRate(series: readonly { t: number; amount: number }[]): number | null {
  let rate = 0.1;
  for (let attempt = 0; attempt < 50; attempt += 1) {
    const value = npv(rate, series);
    const slope = dNpv(rate, series);
    if (!Number.isFinite(value) || !Number.isFinite(slope) || slope === 0) break;
    const next = rate - value / slope;
    if (!Number.isFinite(next) || next <= -0.999999) break;
    if (Math.abs(next - rate) < 1e-12) {
      return Math.abs(npv(next, series)) <= tolerance(series) ? next : null;
    }
    rate = next;
  }
  return bisect(series);
}

function bisect(series: readonly { t: number; amount: number }[]): number | null {
  const samples: { rate: number; value: number }[] = [];
  for (let step = 0; step <= 200; step += 1) {
    const rate = -0.9 + (step * 10.9) / 200;
    const value = npv(rate, series);
    if (Number.isFinite(value)) samples.push({ rate, value });
  }
  for (let index = 1; index < samples.length; index += 1) {
    const left = samples[index - 1];
    const right = samples[index];
    if (!left || !right) continue;
    if (left.value === 0) return left.rate;
    if (left.value * right.value > 0) continue;
    let lo = left.rate;
    let hi = right.rate;
    let loValue = left.value;
    for (let step = 0; step < 80; step += 1) {
      const mid = (lo + hi) / 2;
      const value = npv(mid, series);
      if (!Number.isFinite(value)) return null;
      if (Math.abs(value) <= tolerance(series)) return mid;
      if (loValue * value <= 0) hi = mid;
      else {
        lo = mid;
        loValue = value;
      }
    }
    const mid = (lo + hi) / 2;
    return Math.abs(npv(mid, series)) <= tolerance(series) ? mid : null;
  }
  return null;
}

function npv(rate: number, series: readonly { t: number; amount: number }[]): number {
  let total = 0;
  for (const point of series) total += point.amount / (1 + rate) ** point.t;
  return total;
}

function dNpv(rate: number, series: readonly { t: number; amount: number }[]): number {
  let total = 0;
  for (const point of series) {
    if (point.t === 0) continue;
    total += (-point.t * point.amount) / (1 + rate) ** (point.t + 1);
  }
  return total;
}

function tolerance(series: readonly { t: number; amount: number }[]): number {
  let scale = 0;
  for (const point of series) scale = Math.max(scale, Math.abs(point.amount));
  return Math.max(1e-6, scale * 1e-9);
}

function formatDecimalRate(rate: number): string {
  const negative = rate < 0;
  const scaled = Math.round(Math.abs(rate) * 100_000_000);
  const whole = Math.trunc(scaled / 100_000_000);
  const fraction = String(scaled % 100_000_000).padStart(8, "0");
  return `${negative ? "-" : ""}${whole}.${fraction}`;
}

function formatRatioMinusOne(numerator: bigint, denominator: bigint): string {
  const signed = numerator - denominator;
  const negative = signed < 0n;
  const absolute = negative ? -signed : signed;
  const scale = 100_000_000n;
  const rounded = (absolute * scale + denominator / 2n) / denominator;
  const whole = rounded / scale;
  const fraction = (rounded % scale).toString().padStart(8, "0");
  return `${negative ? "-" : ""}${whole.toString()}.${fraction}`;
}
