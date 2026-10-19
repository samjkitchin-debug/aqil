import "server-only";

import {
  SAXO_MONTH_PERFORMANCE_FIELDS,
  normaliseSaxoPerformance,
  saxoMonthPerformanceQuery,
  type SaxoPerformanceState,
} from "./performance";
import { normaliseSaxoPortfolio } from "./portfolio";
import { refreshSaxoTokens } from "./refresh-flight";
import { captureCurrentAccount } from "./current-account";
import { saxoAllowsRequest, saxoReadUrl, type SaxoEnvironment } from "./sim-guard";
import { readBrokerPortfolio, readSaxoSession, writeBrokerPortfolio, writeSaxoSession } from "./sim-session";
import path from "node:path";

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
    const refreshed = await refreshSaxoTokens({
      userId: input.userId,
      environment: input.environment,
      refreshToken: session.refreshToken,
      appKey: input.appKey,
      appSecret: input.appSecret,
      redirectUri: input.redirectUri,
      fetchImpl: fetch,
      persist: (tokens) => writeSaxoSession(input.userId, input.environment, tokens, input.encryptionKey, input.nowMs),
    });
    if (!refreshed.ok) return "refresh_failed";
    accessToken = refreshed.tokens.accessToken;
  }

  const captured = await captureCurrentAccount({
    userId: input.userId,
    environment: input.environment,
    accessToken,
    encryptionKey: input.encryptionKey,
    archiveRoot: sourceRoot(input.userId, input.environment),
    nowMs: input.nowMs,
    fetchImpl: fetch,
    sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    refresh: async () => {
      const sessionNow = await readSaxoSession(input.userId, input.environment, input.encryptionKey, Date.now());
      const refreshed = await refreshSaxoTokens({
        userId: input.userId,
        environment: input.environment,
        refreshToken: sessionNow?.refreshToken ?? "",
        appKey: input.appKey,
        appSecret: input.appSecret,
        redirectUri: input.redirectUri,
        fetchImpl: fetch,
        persist: (tokens) => writeSaxoSession(input.userId, input.environment, tokens, input.encryptionKey, Date.now()),
      });
      return refreshed.ok ? refreshed.tokens.accessToken : null;
    },
  });
  const previous = await readBrokerPortfolio(input.userId);
  const previousSame = previous?.environment === input.environment ? previous : null;
  if (captured.outcome !== "complete") return "incomplete_kept";

  const retrievedAt = new Date(input.nowMs).toISOString();
  const portfolio = normaliseSaxoPortfolio({
    environment: input.environment,
    retrievedAt,
    pagesComplete: true,
    accountsBody: captured.accountsBody,
    clientBalance: captured.clientBalance,
    accountBalances: captured.accountBalances,
    positionsBody: captured.positionsBody,
    netPositionsBody: captured.netPositionsBody,
  });
  portfolio.performance = await readMonthPerformance(accessToken, input.environment, captured.clientKey, retrievedAt);
  if (portfolio.performance.status !== "ok" && previousSame?.performance?.status === "ok") {
    portfolio.performance = previousSame.performance;
  }
  await writeBrokerPortfolio(input.userId, portfolio);
  return "ok";
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

function sourceRoot(userId: string, environment: SaxoEnvironment): string {
  const cwd = process.cwd().replace(/\\/g, "/");
  const web = cwd.endsWith("/apps/web") ? cwd : path.join(cwd, "apps", "web");
  return path.join(web, ".local", "saxo-source", userId, environment);
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

