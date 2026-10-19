import { latestVerified, type AcquisitionManifest } from "./archive.ts";
import { collectDataset, type DatasetReport } from "./current-account.ts";
import type { SaxoEnvironment } from "./sim-guard.ts";

export type HistoryWindow = { from: string; to: string };

/** Inclusive calendar-month windows. Dates are YYYY-MM-DD in UTC. */
export function monthWindows(fromDate: string, toDate: string): HistoryWindow[] {
  const start = parseDate(fromDate);
  const end = parseDate(toDate);
  if (!start || !end || start > end) return [];
  const windows: HistoryWindow[] = [];
  let cursor = start;
  while (cursor <= end) {
    const monthEnd = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 0));
    const to = monthEnd < end ? monthEnd : end;
    windows.push({ from: formatDate(cursor), to: formatDate(to) });
    cursor = new Date(Date.UTC(to.getUTCFullYear(), to.getUTCMonth(), to.getUTCDate() + 1));
  }
  return windows;
}

export function historyAlreadyComplete(
  manifest: AcquisitionManifest,
  dataset: string,
  scope: string,
  window: string,
): boolean {
  return latestVerified(manifest, { dataset, scope, window }) !== null;
}

/** A successful empty page does not prove there is no earlier history. */
export function emptyWindowEndsHistory(httpStatus: number, rows: number | null): boolean {
  return httpStatus === 200 && rows === 0 ? false : httpStatus === 200 && rows !== null && rows > 0;
}

export function duplicateIds(ids: readonly string[]): string[] {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  for (const id of ids) {
    if (seen.has(id)) duplicates.add(id);
    seen.add(id);
  }
  return [...duplicates];
}

export function sharedIds(left: readonly string[], right: readonly string[]): string[] {
  const rightSet = new Set(right);
  return [...new Set(left.filter((id) => rightSet.has(id)))];
}

export function onlyIn(left: readonly string[], right: readonly string[]): string[] {
  const rightSet = new Set(right);
  return [...new Set(left.filter((id) => !rightSet.has(id)))];
}

/** Dates after the retrieval day are period labels, not observed valuations. */
export function futureLabels(dates: readonly string[], asOf: string): string[] {
  return dates.filter((date) => date > asOf);
}

const CONSTRUCTED_AMOUNT_TYPES = new Set([-3, -4, -5, -6, -9, -13]);

export function amountKind(input: { amountTypeId: number | null; amountType: string | null; affectsBalance: boolean | null }): "booked" | "constructed" | "unknown" {
  if (input.amountTypeId !== null && CONSTRUCTED_AMOUNT_TYPES.has(input.amountTypeId)) return "constructed";
  if (input.affectsBalance === true) return "booked";
  if (input.amountType && /dividend|withholding|commission|fee|deposit|withdrawal|interest|tax|share amount|cash amount/i.test(input.amountType)) {
    return "booked";
  }
  return "unknown";
}

export async function collectHistoricalWindow(input: {
  userId: string;
  environment: SaxoEnvironment;
  accessToken: string;
  encryptionKey: Buffer;
  archiveRoot: string;
  nowMs: number;
  fetchImpl: Parameters<typeof collectDataset>[0]["fetchImpl"];
  sleep?: (ms: number) => Promise<void>;
  refresh?: () => Promise<string | null>;
  dataset: string;
  pathAndQuery: string;
  clientKey: string | null;
  accountKey: string | null;
  reports: DatasetReport[];
}): Promise<{ token: string; body: unknown; complete: boolean; deferred: boolean }> {
  return collectDataset({
    ...input,
    sleep: input.sleep ?? (async () => undefined),
  });
}

function parseDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(date: Date): string {
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${date.getUTCFullYear()}-${month}-${day}`;
}
