import { SAXO_SIM_API_ORIGIN, saxoEndpointFamily, saxoNextUrl, type SaxoEnvironment } from "./sim-guard.ts";

export type ContinuationResult =
  | { ok: true; pathAndQuery: string; normalised: string }
  | { ok: false; reason: "foreign" | "family" | "scope" | "loop" | "poll" | "invalid" };

export function pageCursors(body: unknown): { next: string | null; poll: string | null } {
  const record = asRecord(body);
  return {
    next: text(record?.__next),
    poll: text(record?.__nextPoll),
  };
}

export function continuationPath(input: {
  next: unknown;
  environment: SaxoEnvironment;
  endpointFamily: string;
  clientKey: string | null;
  accountKey: string | null;
  seen: readonly string[];
}): ContinuationResult {
  if (typeof input.next !== "string" || input.next.length === 0) return { ok: false, reason: "invalid" };
  if (input.next.includes("__nextPoll")) return { ok: false, reason: "poll" };
  const url = saxoNextUrl(input.next, input.environment);
  if (!url) return { ok: false, reason: "foreign" };
  const parsed = new URL(url);
  if (parsed.origin !== SAXO_SIM_API_ORIGIN) return { ok: false, reason: "foreign" };
  const prefix = input.environment === "live" ? "/openapi" : "/sim/openapi";
  if (!parsed.pathname.startsWith(prefix)) return { ok: false, reason: "foreign" };
  const pathAndQuery = `${parsed.pathname.slice(prefix.length)}${parsed.search}`;
  const family = saxoEndpointFamily(pathAndQuery);
  if (family !== input.endpointFamily) return { ok: false, reason: "family" };
  if (!scopeMatches(parsed, input.clientKey, input.accountKey)) return { ok: false, reason: "scope" };
  const normalised = normalisedUrl(parsed);
  if (input.seen.includes(normalised)) return { ok: false, reason: "loop" };
  return { ok: true, pathAndQuery, normalised };
}

export function duplicateIdentityPage(pageKeys: readonly string[], seen: ReadonlySet<string>): boolean {
  return pageKeys.length > 0 && pageKeys.every((key) => seen.has(key));
}

export function collectionTruncated(body: unknown, cursorRemains: boolean): boolean {
  const record = asRecord(body);
  const data = arrayData(record);
  const maxRows = record?.MaxRows;
  const count = record?.__count;
  if (!data || typeof maxRows !== "number" || typeof count !== "number") return false;
  return data.length === maxRows && count > data.length && !cursorRemains;
}

/** Saxo can set `__count` to the page length and omit `__next` while more rows exist. */
export function cappedWithoutContinuation(body: unknown, requestedTop: number): boolean {
  const record = asRecord(body);
  const data = arrayData(record);
  if (!data || requestedTop <= 0) return false;
  if (text(record?.__next)) return false;
  if (data.length !== requestedTop) return false;
  const count = record?.__count;
  return typeof count !== "number" || count === data.length;
}

export function withSkip(pathAndQuery: string, skip: number, top: number): string {
  const [path, query = ""] = pathAndQuery.split("?");
  const params = new URLSearchParams(query);
  params.set("$skip", String(skip));
  params.set("$top", String(top));
  return `${path}?${params.toString()}`;
}

export function windowComplete(input: {
  rowCount: number;
  reportedCount: number | null;
  cursorRemains: boolean;
  truncated: boolean;
  loop: boolean;
  duplicate: boolean;
}): boolean {
  if (input.cursorRemains || input.truncated || input.loop || input.duplicate) return false;
  if (input.reportedCount !== null && input.rowCount < input.reportedCount) return false;
  return true;
}

const PERFORMANCE_ROOTS = [
  "AccountSummary",
  "BalancePerformance",
  "TimeWeightedPerformance",
  "Balance",
  "TimeWeighted",
  "MoneyWeighted",
  "InceptionDay",
  "Currency",
  "From",
];

export function performanceObjectComplete(body: unknown): boolean {
  const record = asRecord(body);
  if (!record) return false;
  return PERFORMANCE_ROOTS.some((key) => record[key] != null);
}

function scopeMatches(url: URL, clientKey: string | null, accountKey: string | null): boolean {
  if (clientKey) {
    const queryKey = url.searchParams.get("ClientKey");
    const inPath = url.pathname.split("/").some((part) => decodePart(part) === clientKey);
    if (queryKey && queryKey !== clientKey) return false;
    if (inPath && !queryKey) return true;
    if (queryKey === null && !inPath) return true;
  }
  if (accountKey) {
    if (url.searchParams.get("AccountKey") !== accountKey) return false;
  } else if (url.searchParams.has("AccountKey")) {
    return false;
  }
  return true;
}

function normalisedUrl(url: URL): string {
  const params = [...url.searchParams.entries()].sort(([left], [right]) => left.localeCompare(right));
  const next = new URL(url.origin + url.pathname);
  for (const [key, value] of params) next.searchParams.append(key, value);
  return next.toString();
}

function decodePart(part: string): string {
  try {
    return decodeURIComponent(part);
  } catch {
    return part;
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function arrayData(record: Record<string, unknown> | null): unknown[] | null {
  const data = record?.Data;
  return Array.isArray(data) ? data : null;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}
