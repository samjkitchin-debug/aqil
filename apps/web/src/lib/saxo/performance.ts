export const SAXO_MONTH_PERFORMANCE_FIELDS = [
  "Balance_AccountValue",
  "TimeWeighted_Accumulated",
  "Balance_CashTransfer",
  "Balance_SecurityTransfer",
] as const;

export type SaxoPerformancePoint = { date: string; value: string };

/** Saxo month series. Account value includes contributions. The return is a fraction, not a percentage. */
export type SaxoPerformanceSeries = {
  status: "ok";
  source: "saxo";
  scope: "client";
  period: "Month";
  currency: string | null;
  retrievedAt: string;
  fieldGroups: string[];
  accountValue: SaxoPerformancePoint[];
  timeWeightedAccumulated: SaxoPerformancePoint[];
  returnUnit: "fraction";
};

export type SaxoPerformanceState =
  | SaxoPerformanceSeries
  | { status: "unavailable"; retrievedAt: string; httpStatus: number | null };

export function saxoMonthPerformanceQuery(clientKey: string): string {
  const params = new URLSearchParams({
    ClientKey: clientKey,
    StandardPeriod: "Month",
    FieldGroups: SAXO_MONTH_PERFORMANCE_FIELDS.join(","),
  });
  return `/hist/v4/performance/timeseries?${params.toString()}`;
}

/**
 * Maps a documented timeseries body. Accumulated values above a fraction's plausible range are refused
 * so a percentage is not labelled as a fraction.
 */
export function normaliseSaxoPerformance(input: {
  retrievedAt: string;
  body: unknown;
  fieldGroups: readonly string[];
}): SaxoPerformanceSeries | null {
  const body = record(input.body);
  if (!body) return null;
  const accountValue = points(record(body.Balance)?.AccountValue);
  const accumulated = points(record(body.TimeWeighted)?.Accumulated);
  if (accountValue.length === 0 && accumulated.length === 0) return null;
  if (accumulated.some((point) => Math.abs(Number(point.value)) >= 5)) return null;
  const currency = text(body, "Currency");
  return {
    status: "ok",
    source: "saxo",
    scope: "client",
    period: "Month",
    currency,
    retrievedAt: input.retrievedAt,
    fieldGroups: [...input.fieldGroups],
    accountValue,
    timeWeightedAccumulated: accumulated,
    returnUnit: "fraction",
  };
}

export function formatAccumulatedReturn(value: string | null): string | null {
  if (value === null) return null;
  const fraction = Number(value);
  if (!Number.isFinite(fraction)) return null;
  return new Intl.NumberFormat("en-GB", {
    style: "percent",
    maximumFractionDigits: 1,
    signDisplay: "exceptZero",
  }).format(fraction);
}

function points(value: unknown): SaxoPerformancePoint[] {
  if (!Array.isArray(value)) return [];
  const rows: SaxoPerformancePoint[] = [];
  for (const item of value) {
    const row = record(item);
    const date = text(row, "Date");
    const amount = row?.Value;
    if (!date || typeof amount !== "number" || !Number.isFinite(amount)) continue;
    rows.push({ date, value: String(amount) });
  }
  return rows;
}

function record(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function text(source: Record<string, unknown> | null, key: string): string | null {
  const value = source?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}
