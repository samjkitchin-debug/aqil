import { createHash } from "node:crypto";

import { writeEncryptedUnit } from "./archive.ts";
import { attemptClassified, quotaPace, readQuota, saxoErrorCode } from "./errors.ts";
import {
  cappedWithoutContinuation,
  collectionTruncated,
  continuationPath,
  duplicateIdentityPage,
  pageCursors,
  windowComplete,
  withSkip,
} from "./pagination.ts";
import { indexSourceEvents } from "./source-identity.ts";
import { saxoAccountRefs, saxoAllowsRequest, saxoClientKey, saxoEndpointFamily, saxoReadUrl, type SaxoEnvironment } from "./sim-guard.ts";

const POSITION_FIELDS = "PositionBase,PositionView,DisplayAndFormat,Costs,ExchangeInfo";
const NET_FIELDS = "NetPositionBase,NetPositionView,DisplayAndFormat";
const PAGE_SAFETY = 40;

type FetchLike = (input: string, init: { method: string; headers: Record<string, string> }) => Promise<{
  status: number;
  headers: { get(name: string): string | null };
  text: () => Promise<string>;
}>;

export type DatasetReport = {
  dataset: string;
  httpStatus: number;
  complete: boolean;
  rows: number | null;
  errorCode: string | null;
};

export type CurrentCapture = {
  outcome: "complete" | "partial" | "deferred";
  accountsBody: unknown;
  clientBalance: unknown;
  accountBalances: unknown[];
  positionsBody: unknown;
  netPositionsBody: unknown | null;
  clientKey: string | null;
  reports: DatasetReport[];
};

export async function captureCurrentAccount(input: {
  userId: string;
  environment: SaxoEnvironment;
  accessToken: string;
  encryptionKey: Buffer;
  archiveRoot: string;
  nowMs: number;
  fetchImpl: FetchLike;
  sleep?: (ms: number) => Promise<void>;
  refresh?: () => Promise<string | null>;
}): Promise<CurrentCapture> {
  const sleep = input.sleep ?? (async () => undefined);
  let token = input.accessToken;
  const reports: DatasetReport[] = [];
  const core = new Set(["clients", "accounts", "balances-client", "positions", "net-positions"]);

  const clients = await collectDataset({ ...input, accessToken: token, sleep, dataset: "clients", pathAndQuery: "/port/v1/clients/me", clientKey: null, accountKey: null, reports, refresh: input.refresh });
  token = clients.token;
  if (clients.deferred) return deferred(reports);
  const clientKey = saxoClientKey(clients.body);

  const accounts = await collectDataset({ ...input, accessToken: token, sleep, dataset: "accounts", pathAndQuery: "/port/v1/accounts/me?$top=50", clientKey, accountKey: null, reports, refresh: input.refresh });
  token = accounts.token;
  if (accounts.deferred) return deferred(reports);

  await collectDataset({ ...input, accessToken: token, sleep, dataset: "users", pathAndQuery: "/port/v1/users/me", clientKey, accountKey: null, reports, refresh: input.refresh });
  if (clientKey) {
    await collectDataset({
      ...input,
      accessToken: token,
      sleep,
      dataset: "account-groups",
      pathAndQuery: `/port/v1/accountgroups?ClientKey=${encodeURIComponent(clientKey)}&$top=50`,
      clientKey,
      accountKey: null,
      reports,
      refresh: input.refresh,
    });
  }

  const clientBalance = await collectDataset({
    ...input,
    accessToken: token,
    sleep,
    dataset: "balances-client",
    pathAndQuery: "/port/v1/balances/me",
    clientKey,
    accountKey: null,
    reports,
    refresh: input.refresh,
  });
  token = clientBalance.token;
  if (clientBalance.deferred) return deferred(reports);

  const accountBalances: unknown[] = [];
  for (const account of saxoAccountRefs(accounts.body, clientKey)) {
    const balance = await collectDataset({
      ...input,
      accessToken: token,
      sleep,
      dataset: `balances-account`,
      pathAndQuery: `/port/v1/balances?ClientKey=${encodeURIComponent(account.clientKey)}&AccountKey=${encodeURIComponent(account.accountKey)}`,
      clientKey: account.clientKey,
      accountKey: account.accountKey,
      reports,
      refresh: input.refresh,
    });
    token = balance.token;
    if (balance.deferred) return deferred(reports);
    if (balance.complete && balance.body) accountBalances.push(balance.body);
  }

  const positions = await collectDataset({
    ...input,
    accessToken: token,
    sleep,
    dataset: "positions",
    pathAndQuery: `/port/v1/positions/me?$top=50&FieldGroups=${POSITION_FIELDS}`,
    clientKey,
    accountKey: null,
    reports,
    refresh: input.refresh,
  });
  token = positions.token;
  if (positions.deferred) return deferred(reports);

  const netPositions = await collectDataset({
    ...input,
    accessToken: token,
    sleep,
    dataset: "net-positions",
    pathAndQuery: `/port/v1/netpositions/me?$top=50&FieldGroups=${NET_FIELDS}`,
    clientKey,
    accountKey: null,
    reports,
    refresh: input.refresh,
  });
  token = netPositions.token;
  if (netPositions.deferred) return deferred(reports);

  const accountKey = saxoAccountRefs(accounts.body, clientKey)[0]?.accountKey ?? null;
  await collectDataset({ ...input, accessToken: token, sleep, dataset: "closed-positions", pathAndQuery: "/port/v1/closedpositions/me?$top=50", clientKey, accountKey: null, reports, refresh: input.refresh });
  await collectDataset({ ...input, accessToken: token, sleep, dataset: "exposure-instruments", pathAndQuery: "/port/v1/exposure/instruments/me", clientKey, accountKey: null, reports, refresh: input.refresh });
  await collectDataset({ ...input, accessToken: token, sleep, dataset: "exposure-currency", pathAndQuery: "/port/v1/exposure/currency/me", clientKey, accountKey: null, reports, refresh: input.refresh });
  await collectDataset({ ...input, accessToken: token, sleep, dataset: "orders", pathAndQuery: "/port/v1/orders/me", clientKey, accountKey: null, reports, refresh: input.refresh });

  for (const exchangeId of exchangeIds(positions.body, netPositions.body).slice(0, 20)) {
    await collectDataset({
      ...input,
      accessToken: token,
      sleep,
      dataset: "exchange",
      pathAndQuery: `/ref/v1/exchanges/${encodeURIComponent(exchangeId)}`,
      clientKey,
      accountKey: null,
      reports,
      refresh: input.refresh,
    });
  }

  for (const instrument of instrumentsOf(positions.body, netPositions.body).slice(0, 100)) {
    await collectDataset({
      ...input,
      accessToken: token,
      sleep,
      dataset: "instrument",
      pathAndQuery: `/ref/v1/instruments/details/${instrument.uic}/${encodeURIComponent(instrument.assetType)}`,
      clientKey,
      accountKey: null,
      reports,
      refresh: input.refresh,
    });
    if (!accountKey) continue;
    const priceQuery = new URLSearchParams({
      Uic: String(instrument.uic),
      AssetType: instrument.assetType,
      AccountKey: accountKey,
      FieldGroups: "Quote,DisplayAndFormat",
    });
    await collectDataset({
      ...input,
      accessToken: token,
      sleep,
      dataset: "infoprice",
      pathAndQuery: `/trade/v1/infoprices?${priceQuery.toString()}`,
      clientKey,
      accountKey,
      reports,
      refresh: input.refresh,
    });
  }

  const ready = [...core].every((name) => reports.some((report) => report.dataset === name && report.complete));
  const balancesReady = accountBalances.length === saxoAccountRefs(accounts.body, clientKey).length;
  return {
    outcome: ready && balancesReady && accounts.complete && positions.complete ? "complete" : "partial",
    accountsBody: accounts.body,
    clientBalance: clientBalance.body,
    accountBalances,
    positionsBody: positions.body,
    netPositionsBody: netPositions.complete ? netPositions.body : null,
    clientKey,
    reports,
  };
}

function deferred(reports: DatasetReport[]): CurrentCapture {
  return {
    outcome: "deferred",
    accountsBody: null,
    clientBalance: null,
    accountBalances: [],
    positionsBody: null,
    netPositionsBody: null,
    clientKey: null,
    reports,
  };
}

export async function collectDataset(input: {
  userId: string;
  environment: SaxoEnvironment;
  accessToken: string;
  encryptionKey: Buffer;
  archiveRoot: string;
  nowMs: number;
  fetchImpl: FetchLike;
  sleep: (ms: number) => Promise<void>;
  refresh?: () => Promise<string | null>;
  dataset: string;
  pathAndQuery: string;
  clientKey: string | null;
  accountKey: string | null;
  reports: DatasetReport[];
}): Promise<{ token: string; body: unknown; complete: boolean; deferred: boolean }> {
  const family = saxoEndpointFamily(input.pathAndQuery);
  const seenUrls: string[] = [];
  const seenIds = new Set<string>();
  const pages: unknown[] = [];
  let token = input.accessToken;
  let pathAndQuery: string | null = input.pathAndQuery;
  let status = 0;
  let errorCode: string | null = null;
  let deferred = false;
  let loop = false;
  let duplicate = false;
  let truncated = false;
  let cursorRemains = false;

  for (let page = 0; pathAndQuery && page < PAGE_SAFETY; page += 1) {
    const currentPath: string = pathAndQuery;
    const response = await attemptClassified({
      endpointFamily: family ?? input.pathAndQuery,
      sleep: input.sleep,
      refresh: async () => {
        const next = input.refresh ? await input.refresh() : null;
        if (!next) return false;
        token = next;
        return true;
      },
      call: async () => {
        const fetched = await fetchSaxo(input.fetchImpl, token, input.environment, currentPath);
        status = fetched.status;
        errorCode = saxoErrorCode(fetched.body);
        return fetched;
      },
    });
    if (response.deferredMs !== null) {
      deferred = true;
      cursorRemains = true;
      break;
    }
    const pace = quotaPace(response.rateRemaining, response.rateResetMs, Date.now());
    if (pace.defer) {
      deferred = true;
      cursorRemains = true;
      break;
    }
    if (pace.waitMs > 0 && pathAndQuery) await input.sleep(pace.waitMs);
    if (response.status !== 200 || !response.body) break;
    const identities = indexSourceEvents(response.body).map((event) => event.id);
    if (duplicateIdentityPage(identities, seenIds)) {
      duplicate = true;
      break;
    }
    for (const id of identities) seenIds.add(id);
    pages.push(response.body);
    const cursors = pageCursors(response.body);
    const requestedTop = topFrom(currentPath);
    if (!cursors.next && requestedTop !== null && cappedWithoutContinuation(response.body, requestedTop)) {
      const skip = pages.reduce<number>((sum, page) => sum + (arrayLength(page) ?? 0), 0);
      pathAndQuery = withSkip(input.pathAndQuery, skip, requestedTop);
      cursorRemains = true;
      continue;
    }
    if (!cursors.next) {
      cursorRemains = false;
      truncated = collectionTruncated(response.body, false);
      break;
    }
    if (!family) {
      cursorRemains = true;
      break;
    }
    const query = new URLSearchParams(currentPath.split("?")[1] ?? "");
    const next = continuationPath({
      next: cursors.next,
      environment: input.environment,
      endpointFamily: family,
      clientKey: query.get("ClientKey"),
      accountKey: query.get("AccountKey"),
      seen: seenUrls,
    });
    if (!next.ok) {
      loop = next.reason === "loop";
      cursorRemains = true;
      break;
    }
    seenUrls.push(next.normalised);
    pathAndQuery = next.pathAndQuery;
    cursorRemains = true;
  }
  if (pathAndQuery && pages.length >= PAGE_SAFETY) cursorRemains = true;

  const merged = mergePages(pages);
  const reported = reportedCount(pages[0]);
  const rows = arrayLength(merged);
  const complete =
    !deferred &&
    status === 200 &&
    windowComplete({
      rowCount: rows ?? 0,
      reportedCount: reported,
      cursorRemains,
      truncated,
      loop,
      duplicate,
    }) &&
    (rows !== null || !Array.isArray((merged as { Data?: unknown })?.Data));
  const objectComplete = rows === null && status === 200 && !cursorRemains && !loop && !duplicate && !truncated && pages.length === 1;
  const storedComplete = rows === null ? objectComplete : complete;
  await writeEncryptedUnit({
    root: input.archiveRoot,
    key: input.encryptionKey,
    entry: { dataset: input.dataset, scope: input.userId, window: archiveWindow(input.dataset, input.pathAndQuery, input.clientKey, input.accountKey) },
    unitId: String(input.nowMs),
    complete: storedComplete,
    cursor: deferred ? pathAndQuery : null,
    body: {
      endpoint: input.pathAndQuery.split("?")[0],
      scope: { userId: input.userId, clientKey: input.clientKey, accountKey: input.accountKey },
      retrievedAt: new Date(input.nowMs).toISOString(),
      httpStatus: status,
      complete: storedComplete,
      rows,
      reportedCount: reported,
      errorCode,
      pages,
    },
  });
  input.reports.push({
    dataset: input.dataset,
    httpStatus: status,
    complete: storedComplete,
    rows,
    errorCode,
  });
  return { token, body: merged, complete: storedComplete, deferred };
}

async function fetchSaxo(
  fetchImpl: FetchLike,
  accessToken: string,
  environment: SaxoEnvironment,
  pathAndQuery: string,
): Promise<{ status: number; body: unknown; retryAfter: string | null; rateRemaining: number | null; rateResetMs: number | null }> {
  if (!saxoAllowsRequest("GET", pathAndQuery, environment)) return { status: 0, body: null, retryAfter: null, rateRemaining: null, rateResetMs: null };
  const url = saxoReadUrl(pathAndQuery, environment);
  if (!url) return { status: 0, body: null, retryAfter: null, rateRemaining: null, rateResetMs: null };
  try {
    const response = await fetchImpl(url, {
      method: "GET",
      headers: { authorization: `Bearer ${accessToken}`, accept: "application/json" },
    });
    const retryAfter = response.headers.get("retry-after");
    const quota = readQuota(response.headers);
    const text = await response.text();
    if (!text) return { status: response.status, body: null, retryAfter, rateRemaining: quota.remaining, rateResetMs: quota.resetMs };
    try {
      return { status: response.status, body: JSON.parse(text) as unknown, retryAfter, rateRemaining: quota.remaining, rateResetMs: quota.resetMs };
    } catch {
      return { status: response.status, body: null, retryAfter, rateRemaining: quota.remaining, rateResetMs: quota.resetMs };
    }
  } catch {
    return { status: 0, body: null, retryAfter: null, rateRemaining: null, rateResetMs: null };
  }
}

function mergePages(pages: unknown[]): unknown {
  if (pages.length === 0) return null;
  if (pages.length === 1 && !Array.isArray((pages[0] as { Data?: unknown })?.Data)) return pages[0];
  const data = pages.flatMap((page) => {
    if (!page || typeof page !== "object" || !Array.isArray((page as { Data?: unknown }).Data)) return [];
    return (page as { Data: unknown[] }).Data;
  });
  const count = reportedCount(pages[0]);
  return count === null ? { Data: data } : { Data: data, __count: count };
}

function reportedCount(body: unknown): number | null {
  if (!body || typeof body !== "object") return null;
  const count = (body as { __count?: unknown }).__count;
  return typeof count === "number" ? count : null;
}

function topFrom(pathAndQuery: string): number | null {
  const value = new URLSearchParams(pathAndQuery.split("?")[1] ?? "").get("$top");
  if (!value) return null;
  const top = Number(value);
  return Number.isInteger(top) && top > 0 ? top : null;
}

function arrayLength(body: unknown): number | null {
  if (!body || typeof body !== "object" || !Array.isArray((body as { Data?: unknown }).Data)) return null;
  return (body as { Data: unknown[] }).Data.length;
}

/** Archive window label. Account and client keys are never copied into it. */
export function archiveWindow(dataset: string, pathAndQuery: string, clientKey: string | null, accountKey: string | null): string {
  if (dataset === "balances-account") {
    return createHash("sha256").update(`${clientKey ?? ""}:${accountKey ?? ""}`).digest("hex").slice(0, 16);
  }
  if (dataset === "infoprice") {
    const params = new URLSearchParams(pathAndQuery.split("?")[1] ?? "");
    return `${params.get("Uic") ?? "price"}-${params.get("AssetType") ?? "instrument"}`;
  }
  const params = new URLSearchParams(pathAndQuery.split("?")[1] ?? "");
  const from = params.get("FromDate") ?? params.get("FromDateTime")?.slice(0, 10) ?? null;
  const to = params.get("ToDate") ?? params.get("ToDateTime")?.slice(0, 10) ?? null;
  if (from && to) return `${from}_${to}`;
  const pathParts = (pathAndQuery.split("?")[0] ?? "").split("/");
  const pathTo = pathParts.at(-1);
  const pathFrom = pathParts.at(-2);
  if (pathFrom && pathTo && /^\d{4}-\d{2}-\d{2}$/.test(pathFrom) && /^\d{4}-\d{2}-\d{2}$/.test(pathTo)) {
    return `${pathFrom}_${pathTo}`;
  }
  const period = params.get("StandardPeriod");
  if (period) return period;
  if (dataset === "instrument" || dataset === "exchange") {
    const pathOnly = pathAndQuery.split("?")[0] ?? dataset;
    return pathOnly.split("/").filter((part) => part !== clientKey && part !== accountKey).slice(-2).join("/");
  }
  return "current";
}

function exchangeIds(...bodies: unknown[]): string[] {
  const ids = new Set<string>();
  for (const body of bodies) {
    walk(body, (record) => {
      if (typeof record.ExchangeId === "string" && record.ExchangeId.length > 0) ids.add(record.ExchangeId);
    });
  }
  return [...ids];
}

function instrumentsOf(positions: unknown, netPositions: unknown): Array<{ uic: number; assetType: string }> {
  const found: Array<{ uic: number; assetType: string }> = [];
  const seen = new Set<string>();
  for (const body of [positions, netPositions]) {
    for (const event of indexSourceEvents(body)) {
      void event;
    }
    walk(body, (record) => {
      const uic = record.Uic;
      const assetType = record.AssetType;
      if (typeof uic !== "number" || typeof assetType !== "string") return;
      const key = `${uic}:${assetType}`;
      if (seen.has(key)) return;
      seen.add(key);
      found.push({ uic, assetType });
    });
  }
  return found;
}

function walk(value: unknown, visit: (record: Record<string, unknown>) => void): void {
  if (!value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    for (const item of value) walk(item, visit);
    return;
  }
  const record = value as Record<string, unknown>;
  visit(record);
  for (const child of Object.values(record)) walk(child, visit);
}
