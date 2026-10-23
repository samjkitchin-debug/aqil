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

function isLoopbackHost(hostname: string): boolean {
  return hostname === "127.0.0.1" || hostname === "localhost" || hostname === "::1";
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
