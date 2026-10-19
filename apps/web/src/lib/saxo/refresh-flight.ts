import { requestSaxoToken } from "./sim-http.ts";
import type { SaxoEnvironment, SaxoTokens } from "./sim-guard.ts";

type FetchLike = Parameters<typeof requestSaxoToken>[1];

export type RefreshFlightResult =
  | { ok: true; tokens: SaxoTokens }
  | { ok: false; status: number; errorCode: string | null };

const flights = new Map<string, Promise<RefreshFlightResult>>();

/**
 * One refresh at a time for a local process, user and environment.
 * The rotated tokens are persisted before any waiter receives them.
 * This does not protect two operating-system processes.
 */
export function refreshSaxoTokens(input: {
  userId: string;
  environment: SaxoEnvironment;
  refreshToken: string;
  appKey: string;
  appSecret: string;
  redirectUri: string;
  fetchImpl: FetchLike;
  persist: (tokens: SaxoTokens) => Promise<void>;
}): Promise<RefreshFlightResult> {
  const key = `${input.userId}:${input.environment}`;
  const existing = flights.get(key);
  if (existing) return existing;
  const flight = runRefresh(input).finally(() => {
    if (flights.get(key) === flight) flights.delete(key);
  });
  flights.set(key, flight);
  return flight;
}

async function runRefresh(input: {
  environment: SaxoEnvironment;
  refreshToken: string;
  appKey: string;
  appSecret: string;
  redirectUri: string;
  fetchImpl: FetchLike;
  persist: (tokens: SaxoTokens) => Promise<void>;
}): Promise<RefreshFlightResult> {
  const refreshed = await requestSaxoToken(
    {
      grant: "refresh_token",
      environment: input.environment,
      refreshToken: input.refreshToken,
      appKey: input.appKey,
      appSecret: input.appSecret,
      redirectUri: input.redirectUri,
    },
    input.fetchImpl,
  );
  if (!refreshed.ok) return { ok: false, status: refreshed.status, errorCode: refreshed.errorCode };
  await input.persist(refreshed.tokens);
  return { ok: true, tokens: refreshed.tokens };
}
