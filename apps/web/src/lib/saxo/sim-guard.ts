import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

export type SaxoEnvironment = "live" | "simulation";

/** Live and simulation hosts stay separate. A token from one must not call the other. */
export const SAXO_SIM_AUTHORIZE_URL = "https://sim.logonvalidation.net/authorize";
export const SAXO_SIM_TOKEN_URL = "https://sim.logonvalidation.net/token";
export const SAXO_LIVE_AUTHORIZE_URL = "https://live.logonvalidation.net/authorize";
export const SAXO_LIVE_TOKEN_URL = "https://live.logonvalidation.net/token";
export const SAXO_SIM_API_ORIGIN = "https://gateway.saxobank.com";
export const SAXO_SIM_API_PREFIX = "/sim/openapi";
export const SAXO_LIVE_API_PREFIX = "/openapi";

export const SAXO_SIM_REDIRECT_URI = "http://localhost:3000/auth/saxo/callback";
export const SAXO_STATE_COOKIE = "aqil-saxo-sim-state";

const ALLOWED_GET_PREFIXES = [
  "/port/v1/clients/me",
  "/port/v1/users/me",
  "/port/v1/accounts/me",
  "/port/v1/accounts",
  "/port/v1/accountgroups",
  "/port/v1/balances/me",
  "/port/v1/balances",
  "/port/v1/positions/me",
  "/port/v1/positions",
  "/port/v1/netpositions/me",
  "/port/v1/netpositions",
  "/port/v1/closedpositions",
  "/port/v1/exposure",
  "/port/v1/orders",
  "/ref/v1/instruments/details",
  "/ref/v1/exchanges",
  "/trade/v1/infoprices",
  "/chart/v3/charts",
  "/hist/v1/transactions",
  "/hist/v3/positions",
  "/hist/v3/accountvalues",
  "/hist/v3/perf",
  "/hist/v4/performance/summary",
  "/hist/v4/performance/timeseries",
  "/cs/v1/audit/orderactivities",
  "/cs/v1/reports/bookings",
  "/cs/v1/reports/trades",
  "/cs/v1/reports/closedPositions",
  "/cs/v1/reports/aggregatedAmounts",
  "/ca/v2/events",
] as const;

/** Reads of open orders and order history. Every other order path stays refused. */
const ORDER_READ_PREFIXES = ["/port/v1/orders", "/cs/v1/audit/orderactivities"] as const;

const BLOCKED_GET_MARKERS = ["withdraw", "transfer", "subscription", "trade/v2"];

export function saxoDiscoveryAllowed(input: {
  nodeEnv: string | undefined;
  requestHost: string;
  redirectUri: string | undefined;
}): boolean {
  if (input.nodeEnv !== "development") return false;
  const host = input.requestHost.split(":")[0]?.toLowerCase();
  if (host !== "localhost") return false;
  return input.redirectUri === SAXO_SIM_REDIRECT_URI;
}

export function createSaxoState(): string {
  return randomBytes(32).toString("hex");
}

export function saxoEndpoints(environment: SaxoEnvironment): {
  authorizeUrl: string;
  tokenUrl: string;
  apiPrefix: string;
} {
  if (environment === "live") {
    return {
      authorizeUrl: SAXO_LIVE_AUTHORIZE_URL,
      tokenUrl: SAXO_LIVE_TOKEN_URL,
      apiPrefix: SAXO_LIVE_API_PREFIX,
    };
  }
  return {
    authorizeUrl: SAXO_SIM_AUTHORIZE_URL,
    tokenUrl: SAXO_SIM_TOKEN_URL,
    apiPrefix: SAXO_SIM_API_PREFIX,
  };
}

export function saxoAuthorizeUrl(input: {
  appKey: string;
  state: string;
  redirectUri: string;
  environment?: SaxoEnvironment;
}): string {
  const url = new URL(saxoEndpoints(input.environment ?? "simulation").authorizeUrl);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", input.appKey);
  url.searchParams.set("state", input.state);
  url.searchParams.set("redirect_uri", input.redirectUri);
  return url.toString();
}

/**
 * Broker connect stays on local development until encrypted, owner-scoped token storage
 * exists on the hosted database. A production host must not start Saxo authorisation.
 */
export function saxoConnectAllowed(input: {
  environment: SaxoEnvironment;
  nodeEnv: string | undefined;
  requestHost: string;
  redirectUri: string | undefined;
}): boolean {
  if (input.nodeEnv !== "development") return false;
  const host = input.requestHost.split(":")[0]?.toLowerCase();
  if (host !== "localhost" && host !== "127.0.0.1") return false;
  return input.redirectUri === SAXO_SIM_REDIRECT_URI;
}

type StatePayload = { state: string; userId: string; exp: number; environment: SaxoEnvironment };

export function sealSaxoState(payload: StatePayload, secret: string): string {
  const body = Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
  const mac = createHmac("sha256", secret).update(body).digest("base64url");
  return `v1.${body}.${mac}`;
}

export function openSaxoState(sealed: string, secret: string, nowMs: number): StatePayload | null {
  const [version, body, mac] = sealed.split(".");
  if (version !== "v1" || !body || !mac) return null;
  const expected = createHmac("sha256", secret).update(body).digest("base64url");
  const left = Buffer.from(mac);
  const right = Buffer.from(expected);
  if (left.length !== right.length || !timingSafeEqual(left, right)) return null;
  try {
    const parsed = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as StatePayload;
    if (!parsed.state || !parsed.userId || typeof parsed.exp !== "number") return null;
    if (parsed.environment !== "live" && parsed.environment !== "simulation") return null;
    if (parsed.exp < nowMs) return null;
    return parsed;
  } catch {
    return null;
  }
}

export type SaxoTokens = {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  refreshExpiresIn: number;
};

export function parseSaxoTokenResponse(body: unknown): SaxoTokens | null {
  if (!body || typeof body !== "object") return null;
  const record = body as Record<string, unknown>;
  if (typeof record.access_token !== "string" || typeof record.refresh_token !== "string") return null;
  if (typeof record.expires_in !== "number" || typeof record.refresh_token_expires_in !== "number") return null;
  return {
    accessToken: record.access_token,
    refreshToken: record.refresh_token,
    expiresIn: record.expires_in,
    refreshExpiresIn: record.refresh_token_expires_in,
  };
}

/** GET portfolio and reference paths only. Orders, transfers and other methods are refused. */
export function saxoAllowsRequest(method: string, pathAndQuery: string, environment: SaxoEnvironment = "simulation"): boolean {
  return method === "GET" && saxoReadUrl(pathAndQuery, environment) !== null;
}

/** Query or path for a read-only GET. Rejects orders, transfers and other hosts. */
export function saxoReadUrl(pathAndQuery: string, environment: SaxoEnvironment = "simulation"): string | null {
  if (!pathAndQuery.startsWith("/") || pathAndQuery.startsWith("//")) return null;
  if (pathAndQuery.toLowerCase().includes("mockdata")) return null;
  const pathOnly = pathAndQuery.split("?")[0] ?? "";
  const lower = pathOnly.toLowerCase();
  if (BLOCKED_GET_MARKERS.some((marker) => lower.includes(marker))) return null;
  if (lower.includes("order") && !orderReadAllowed(pathOnly)) return null;
  const allowed = ALLOWED_GET_PREFIXES.some(
    (prefix) => pathOnly === prefix || pathOnly.startsWith(`${prefix}/`),
  );
  if (!allowed) return null;
  return `${SAXO_SIM_API_ORIGIN}${saxoEndpoints(environment).apiPrefix}${pathAndQuery}`;
}

/** Follow Saxo `__next` only inside the same environment. Live links are not rewritten onto simulation. */
export function saxoNextUrl(next: unknown, environment: SaxoEnvironment = "simulation"): string | null {
  if (typeof next !== "string" || next.length === 0) return null;
  let url: URL;
  try {
    url = next.startsWith("http") ? new URL(next) : new URL(next, SAXO_SIM_API_ORIGIN);
  } catch {
    return null;
  }
  if (url.origin !== SAXO_SIM_API_ORIGIN) return null;
  const prefix = saxoEndpoints(environment).apiPrefix;
  let pathname = url.pathname;
  if (environment === "simulation" && pathname.startsWith("/openapi/") && !pathname.startsWith("/sim/")) {
    pathname = `/sim${pathname}`;
  }
  if (!pathname.startsWith(prefix)) return null;
  return saxoReadUrl(`${pathname.slice(prefix.length)}${url.search}`, environment);
}

export type SaxoAccountRef = { clientKey: string; accountKey: string };
export type SaxoInstrumentRef = { uic: number; assetType: string };

export function saxoAccountRefs(body: unknown, fallbackClientKey: string | null): SaxoAccountRef[] {
  const rows = arrayData(body);
  const refs: SaxoAccountRef[] = [];
  for (const row of rows) {
    if (!row || typeof row !== "object") continue;
    const record = row as Record<string, unknown>;
    const accountKey = stringField(record, "AccountKey");
    const clientKey = stringField(record, "ClientKey") ?? fallbackClientKey;
    if (clientKey && accountKey) refs.push({ clientKey, accountKey });
  }
  return refs;
}

export function saxoClientKey(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  return stringField(body as Record<string, unknown>, "ClientKey");
}

export function saxoInstrumentRefs(body: unknown): SaxoInstrumentRef[] {
  const found: SaxoInstrumentRef[] = [];
  const seen = new Set<string>();
  walk(body, (record) => {
    const uic = record.Uic;
    const assetType = record.AssetType;
    if (typeof uic !== "number" || typeof assetType !== "string") return;
    const key = `${uic}:${assetType}`;
    if (seen.has(key)) return;
    seen.add(key);
    found.push({ uic, assetType });
  });
  return found;
}

export function saxoEndpointFamily(pathAndQuery: string): string | null {
  const pathOnly = pathAndQuery.split("?")[0] ?? "";
  const match = ALLOWED_GET_PREFIXES.filter((prefix) => pathOnly === prefix || pathOnly.startsWith(`${prefix}/`)).sort(
    (left, right) => right.length - left.length,
  )[0];
  return match ?? null;
}

function orderReadAllowed(pathOnly: string): boolean {
  return ORDER_READ_PREFIXES.some((prefix) => pathOnly === prefix || pathOnly.startsWith(`${prefix}/`));
}

function arrayData(body: unknown): unknown[] {
  if (!body || typeof body !== "object") return [];
  const data = (body as { Data?: unknown }).Data;
  return Array.isArray(data) ? data : [];
}

function stringField(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === "string" && value.length > 0 ? value : null;
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
