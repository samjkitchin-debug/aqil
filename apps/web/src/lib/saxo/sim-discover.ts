import "server-only";

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { catalogueJson, type FieldObservation } from "./redact.ts";
import { saxoArtifactDir, readSaxoSession, writeSaxoSession } from "./sim-session.ts";
import { refreshSaxoTokens } from "./refresh-flight.ts";
import {
  saxoAccountRefs,
  saxoClientKey,
  saxoInstrumentRefs,
  saxoNextUrl,
  saxoReadUrl,
  type SaxoInstrumentRef,
} from "./sim-guard.ts";

export type EndpointResult = {
  id: string;
  status: number;
  fields: FieldObservation[];
};

const PAGE_LIMIT = 3;
const INSTRUMENT_LIMIT = 12;

export async function discoverSaxoSimulation(input: {
  userId: string;
  environment: import("./sim-guard.ts").SaxoEnvironment;
  appKey: string;
  appSecret: string;
  redirectUri: string;
  encryptionKey: Buffer;
  nowMs: number;
}): Promise<{ ok: true; results: EndpointResult[] } | { ok: false; reason: "no_session" | "refresh_failed" }> {
  const session = await readSaxoSession(input.userId, input.environment, input.encryptionKey, input.nowMs);
  if (!session) return { ok: false, reason: "no_session" };

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
    if (!refreshed.ok) return { ok: false, reason: "refresh_failed" };
    accessToken = refreshed.tokens.accessToken;
  }

  const results: EndpointResult[] = [];
  const clients = await capture(results, accessToken, "clients-me", "/port/v1/clients/me");
  await capture(results, accessToken, "users-me", "/port/v1/users/me");
  const accounts = await capture(results, accessToken, "accounts-me", "/port/v1/accounts/me?$top=50");
  await capture(results, accessToken, "balances-me", "/port/v1/balances/me");

  const accountRefs = saxoAccountRefs(accounts, saxoClientKey(clients));
  for (const [index, account] of accountRefs.slice(0, 10).entries()) {
    const query = new URLSearchParams({ ClientKey: account.clientKey, AccountKey: account.accountKey });
    await capture(results, accessToken, `balances-account-${index + 1}`, `/port/v1/balances?${query.toString()}`);
  }

  const positions = await capture(
    results,
    accessToken,
    "positions-me",
    "/port/v1/positions/me?$top=50&FieldGroups=PositionBase,PositionView,DisplayAndFormat",
  );
  const netPositions = await capture(
    results,
    accessToken,
    "netpositions-me",
    "/port/v1/netpositions/me?$top=50&FieldGroups=NetPositionBase,NetPositionView,DisplayAndFormat",
  );

  const instruments = uniqueInstruments([
    ...saxoInstrumentRefs(positions),
    ...saxoInstrumentRefs(netPositions),
  ]).slice(0, INSTRUMENT_LIMIT);
  const accountKey = accountRefs[0]?.accountKey;
  for (const [index, instrument] of instruments.entries()) {
    await capture(
      results,
      accessToken,
      `instrument-${index + 1}`,
      `/ref/v1/instruments/details/${instrument.uic}/${encodeURIComponent(instrument.assetType)}`,
    );
    if (!accountKey) continue;
    const priceQuery = new URLSearchParams({
      Uic: String(instrument.uic),
      AssetType: instrument.assetType,
      AccountKey: accountKey,
      FieldGroups: "Quote,PriceInfo,InstrumentPriceDetails,DisplayAndFormat",
    });
    await capture(results, accessToken, `infoprice-${index + 1}`, `/trade/v1/infoprices?${priceQuery.toString()}`);
  }

  const dir = saxoArtifactDir();
  await mkdir(dir, { recursive: true });
  await writeFile(path.join(dir, "catalogue.json"), JSON.stringify(results, null, 2), {
    encoding: "utf8",
    mode: 0o600,
  });
  return { ok: true, results };
}

async function capture(
  results: EndpointResult[],
  accessToken: string,
  id: string,
  pathAndQuery: string,
): Promise<unknown> {
  const first = await saxoGet(accessToken, pathAndQuery);
  const pages = [first.body];
  let next = saxoNextUrl(objectField(first.body, "__next"));
  let page = 1;
  while (next && page < PAGE_LIMIT) {
    const relative = next.replace(/^https:\/\/gateway\.saxobank\.com\/sim\/openapi/, "");
    const followed = await saxoGet(accessToken, relative);
    pages.push(followed.body);
    next = saxoNextUrl(objectField(followed.body, "__next"));
    page += 1;
  }
  const fields = pages.flatMap((body) => catalogueJson(body));
  results.push({ id, status: first.status, fields: mergeFields(fields) });
  await writeRaw(id, { status: first.status, pages });
  return first.body;
}

async function saxoGet(accessToken: string, pathAndQuery: string): Promise<{ status: number; body: unknown }> {
  const url = saxoReadUrl(pathAndQuery);
  if (!url) return { status: 0, body: null };
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        authorization: `Bearer ${accessToken}`,
        accept: "application/json",
      },
      cache: "no-store",
    });
    const text = await response.text();
    let body: unknown = null;
    if (text) {
      try {
        body = JSON.parse(text) as unknown;
      } catch {
        body = null;
      }
    }
    return { status: response.status, body };
  } catch {
    return { status: 0, body: null };
  }
}

function uniqueInstruments(refs: SaxoInstrumentRef[]): SaxoInstrumentRef[] {
  const seen = new Set<string>();
  const unique: SaxoInstrumentRef[] = [];
  for (const ref of refs) {
    const key = `${ref.uic}:${ref.assetType}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(ref);
  }
  return unique;
}

function objectField(body: unknown, key: string): unknown {
  if (!body || typeof body !== "object") return null;
  return (body as Record<string, unknown>)[key];
}

function mergeFields(fields: FieldObservation[]): FieldObservation[] {
  const map = new Map<string, FieldObservation>();
  for (const field of fields) {
    const existing = map.get(field.path);
    if (!existing) {
      map.set(field.path, { ...field, types: [...field.types] });
      continue;
    }
    for (const type of field.types) {
      if (!existing.types.includes(type)) existing.types.push(type);
    }
    existing.nullable = existing.nullable || field.nullable;
    existing.isoTimestamp = existing.isoTimestamp || field.isoTimestamp;
  }
  return [...map.values()];
}

async function writeRaw(id: string, payload: unknown): Promise<void> {
  const dir = saxoArtifactDir();
  await mkdir(dir, { recursive: true });
  await writeFile(path.join(dir, `${id}.json`), JSON.stringify(payload), { encoding: "utf8", mode: 0o600 });
}
