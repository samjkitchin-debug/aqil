import "server-only";

import {
  SAXO_MONTH_PERFORMANCE_FIELDS,
  normaliseSaxoPerformance,
  saxoMonthPerformanceQuery,
  type SaxoPerformanceState,
} from "./performance";
import { normaliseSaxoPortfolio } from "./portfolio";
import { requestSaxoToken } from "./sim-http";
import {
  saxoAccountRefs,
  saxoAllowsRequest,
  saxoClientKey,
  saxoNextUrl,
  saxoReadUrl,
  type SaxoEnvironment,
} from "./sim-guard";
import { readBrokerPortfolio, readSaxoSession, writeBrokerPortfolio, writeSaxoSession } from "./sim-session";

const PAGE_LIMIT = 10;

export async function syncSaxoPortfolio(input: {
  userId: string;
  environment: SaxoEnvironment;
  appKey: string;
  appSecret: string;
  redirectUri: string;
  encryptionKey: Buffer;
  nowMs: number;
}): Promise<"ok" | "no_session" | "refresh_failed" | "source_error" | "incomplete_kept"> {
  const session = await readSaxoSession(input.userId, input.environment, input.encryptionKey, input.nowMs);
  if (!session || session.environment !== input.environment) return "no_session";

  let accessToken = session.accessToken;
  if (session.accessExpiresAt <= input.nowMs + 15_000) {
    const refreshed = await requestSaxoToken(
      {
        grant: "refresh_token",
        environment: input.environment,
        refreshToken: session.refreshToken,
        appKey: input.appKey,
        appSecret: input.appSecret,
        redirectUri: input.redirectUri,
      },
      fetch,
    );
    if (!refreshed.ok) return "refresh_failed";
    await writeSaxoSession(input.userId, input.environment, refreshed.tokens, input.encryptionKey, input.nowMs);
    accessToken = refreshed.tokens.accessToken;
  }

  const accounts = await readCollection(accessToken, input.environment, "/port/v1/accounts/me?$top=50");
  const positions = await readCollection(
    accessToken,
    input.environment,
    "/port/v1/positions/me?$top=50&FieldGroups=PositionBase,PositionView,DisplayAndFormat",
  );
  const netPositions = await readCollection(
    accessToken,
    input.environment,
    "/port/v1/netpositions/me?$top=50&FieldGroups=NetPositionBase,NetPositionView,DisplayAndFormat",
  );
  if (!accounts.ok || !positions.ok) return "source_error";

  const client = await readOne(accessToken, input.environment, "/port/v1/clients/me");
  const clientBalance = await readOne(accessToken, input.environment, "/port/v1/balances/me");
  const clientKey = saxoClientKey(client.body);
  const balances: unknown[] = [];
  for (const account of saxoAccountRefs(accounts.body, clientKey).slice(0, 10)) {
    const query = new URLSearchParams({ ClientKey: account.clientKey, AccountKey: account.accountKey });
    const balance = await readOne(accessToken, input.environment, `/port/v1/balances?${query.toString()}`);
    if (balance.status === 200) balances.push(balance.body);
  }

  const pagesComplete = accounts.complete && positions.complete && (!netPositions.ok || netPositions.complete);
  const previous = await readBrokerPortfolio(input.userId);
  const previousSame = previous?.environment === input.environment ? previous : null;
  if (!pagesComplete && previousSame?.coverage?.accounts) return "incomplete_kept";

  const retrievedAt = new Date(input.nowMs).toISOString();
  const portfolio = normaliseSaxoPortfolio({
    environment: input.environment,
    retrievedAt,
    pagesComplete,
    accountsBody: accounts.body,
    clientBalance: clientBalance.body,
    accountBalances: balances,
    positionsBody: positions.body,
    netPositionsBody: netPositions.ok ? netPositions.body : null,
  });
  portfolio.performance = await readMonthPerformance(accessToken, input.environment, saxoClientKey(client.body), retrievedAt);
  if (portfolio.performance.status !== "ok" && previousSame?.performance?.status === "ok") {
    portfolio.performance = previousSame.performance;
  }
  await writeBrokerPortfolio(input.userId, portfolio);
  return pagesComplete ? "ok" : "incomplete_kept";
}

async function readCollection(
  accessToken: string,
  environment: SaxoEnvironment,
  pathAndQuery: string,
): Promise<{ ok: boolean; complete: boolean; body: unknown }> {
  const first = await readOne(accessToken, environment, pathAndQuery);
  if (first.status === 429 || first.status === 503 || first.status === 401 || first.status === 0) {
    return { ok: false, complete: false, body: null };
  }
  if (first.status !== 200) return { ok: false, complete: false, body: null };
  const pages = [first.body];
  let next = saxoNextUrl(objectField(first.body, "__next"), environment);
  let page = 1;
  while (next && page < PAGE_LIMIT) {
    const relative = next.replace(/^https:\/\/gateway\.saxobank\.com(?:\/sim)?\/openapi/, "");
    const followed = await readOne(accessToken, environment, relative);
    if (followed.status !== 200) return { ok: false, complete: false, body: null };
    pages.push(followed.body);
    next = saxoNextUrl(objectField(followed.body, "__next"), environment);
    page += 1;
  }
  const merged = mergePages(pages);
  return { ok: true, complete: next === null || countedRowsCovered(merged), body: merged };
}

async function readOne(
  accessToken: string,
  environment: SaxoEnvironment,
  pathAndQuery: string,
): Promise<{ status: number; body: unknown }> {
  if (!saxoAllowsRequest("GET", pathAndQuery, environment)) return { status: 0, body: null };
  const url = saxoReadUrl(pathAndQuery, environment);
  if (!url) return { status: 0, body: null };
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { authorization: `Bearer ${accessToken}`, accept: "application/json" },
      cache: "no-store",
    });
    const text = await response.text();
    if (!text) return { status: response.status, body: null };
    try {
      return { status: response.status, body: JSON.parse(text) as unknown };
    } catch {
      return { status: response.status, body: null };
    }
  } catch {
    return { status: 0, body: null };
  }
}

function countedRowsCovered(body: unknown): boolean {
  if (!body || typeof body !== "object") return false;
  const record = body as { __count?: unknown; Data?: unknown };
  return typeof record.__count === "number" && Array.isArray(record.Data) && record.Data.length >= record.__count;
}

function mergePages(pages: unknown[]): unknown {
  const data = pages.flatMap((page) => {
    if (!page || typeof page !== "object" || !Array.isArray((page as { Data?: unknown }).Data)) return [];
    return (page as { Data: unknown[] }).Data;
  });
  return { Data: data };
}

async function readMonthPerformance(
  accessToken: string,
  environment: SaxoEnvironment,
  clientKey: string | null,
  retrievedAt: string,
): Promise<SaxoPerformanceState> {
  if (!clientKey) return { status: "unavailable", retrievedAt, httpStatus: null };
  const response = await readOne(accessToken, environment, saxoMonthPerformanceQuery(clientKey));
  if (response.status !== 200) return { status: "unavailable", retrievedAt, httpStatus: response.status };
  const series = normaliseSaxoPerformance({
    retrievedAt,
    body: response.body,
    fieldGroups: SAXO_MONTH_PERFORMANCE_FIELDS,
  });
  return series ?? { status: "unavailable", retrievedAt, httpStatus: response.status };
}

function objectField(body: unknown, key: string): unknown {
  if (!body || typeof body !== "object") return null;
  return (body as Record<string, unknown>)[key];
}
