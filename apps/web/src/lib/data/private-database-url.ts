const LOCAL_RESEARCH_DATABASE_URL =
  "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres";

const LOCAL_ETF_DATABASE_URL =
  "postgresql://research_worker:research_worker@127.0.0.1:55432/aqil_etf";

export const RESEARCH_DATABASE_UNAVAILABLE = "The research database is not configured.";

export const RESEARCH_DATABASE_LOCAL_REFUSED =
  "A local database address is not used in production.";

export const ETF_DATABASE_UNAVAILABLE = "The ETF database is not configured.";

export const ETF_DATABASE_LOCAL_ONLY =
  "ETF research reads only the local aqil_etf database.";

export type ResolvedDatabaseUrl =
  | { status: "configured"; url: string }
  | { status: "unavailable"; reason: string };

export type DatabaseUrlInput = {
  nodeEnv: string | undefined;
  configuredUrl: string | undefined;
};

function trimmed(value: string | undefined): string {
  return value?.trim() ?? "";
}

function normalisedHost(hostname: string): string {
  const bare = hostname.startsWith("[") && hostname.endsWith("]") ? hostname.slice(1, -1) : hostname;
  return bare.toLowerCase().replace(/\.$/, "");
}

function isIpv4Loopback(host: string): boolean {
  const parts = host.split(".");
  if (parts.length !== 4 || parts.some((part) => !/^\d{1,3}$/.test(part))) return false;
  const numbers = parts.map((part) => Number(part));
  if (numbers.some((part) => part > 255)) return false;
  return numbers[0] === 127;
}

/** Node keeps brackets on a postgresql IPv6 host, and maps ::ffff:127.0.0.1 to hex. */
function isIpv4MappedLoopback(host: string): boolean {
  const dotted = host.match(/^::ffff:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/);
  if (dotted?.[1]) return isIpv4Loopback(dotted[1]);
  const hex = host.match(/^::ffff:([0-9a-f]{1,4}):([0-9a-f]{1,4})$/);
  if (!hex?.[1] || !hex[2]) return false;
  const high = Number.parseInt(hex[1], 16);
  return (high >> 8) === 127;
}

function isLoopbackHost(hostname: string): boolean {
  const host = normalisedHost(hostname);
  if (host === "localhost" || host === "::1" || host === "0.0.0.0" || host === "::") return true;
  if (isIpv4Loopback(host) || isIpv4MappedLoopback(host)) return true;
  return false;
}

function parseDatabaseUrl(value: string): URL | null {
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

export function resolveResearchDatabaseUrl(input: DatabaseUrlInput): ResolvedDatabaseUrl {
  const configured = trimmed(input.configuredUrl);
  if (input.nodeEnv === "production") {
    if (!configured) {
      return { status: "unavailable", reason: RESEARCH_DATABASE_UNAVAILABLE };
    }
    const parsed = parseDatabaseUrl(configured);
    if (!parsed || isLoopbackHost(parsed.hostname)) {
      return { status: "unavailable", reason: RESEARCH_DATABASE_LOCAL_REFUSED };
    }
    return { status: "configured", url: configured };
  }
  if (!configured) return { status: "configured", url: LOCAL_RESEARCH_DATABASE_URL };
  return { status: "configured", url: configured };
}

export function resolveEtfDatabaseUrl(input: DatabaseUrlInput): ResolvedDatabaseUrl {
  const configured = trimmed(input.configuredUrl);
  if (input.nodeEnv === "production") {
    if (!configured) {
      return { status: "unavailable", reason: ETF_DATABASE_UNAVAILABLE };
    }
    const parsed = parseDatabaseUrl(configured);
    if (!parsed || isLoopbackHost(parsed.hostname)) {
      return { status: "unavailable", reason: RESEARCH_DATABASE_LOCAL_REFUSED };
    }
    return { status: "configured", url: configured };
  }

  const candidate = configured || LOCAL_ETF_DATABASE_URL;
  const parsed = parseDatabaseUrl(candidate);
  if (!parsed) return { status: "unavailable", reason: ETF_DATABASE_LOCAL_ONLY };
  if (parsed.hostname !== "127.0.0.1" && parsed.hostname !== "localhost") {
    return { status: "unavailable", reason: ETF_DATABASE_LOCAL_ONLY };
  }
  if (parsed.port !== "55432") return { status: "unavailable", reason: ETF_DATABASE_LOCAL_ONLY };
  if (parsed.pathname !== "/aqil_etf") return { status: "unavailable", reason: ETF_DATABASE_LOCAL_ONLY };
  return { status: "configured", url: candidate };
}
