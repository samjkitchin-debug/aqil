import "server-only";

import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { classifySaxoLink, type SaxoLinkState } from "./link-state";
import { repairStoredPortfolio, type BrokerPortfolioView } from "./portfolio";
import type { SaxoEnvironment, SaxoTokens } from "./sim-guard";
import { decryptJson, encryptJson } from "./token-crypto";

type StoredSession = {
  userId: string;
  environment: SaxoEnvironment;
  accessToken: string;
  refreshToken: string;
  accessExpiresAt: number;
  refreshExpiresAt: number;
};

function webRoot(): string {
  const cwd = process.cwd();
  return cwd.replace(/\\/g, "/").endsWith("/apps/web") ? cwd : path.join(cwd, "apps", "web");
}

function vaultDir(): string {
  return path.join(webRoot(), ".local", "saxo-vault");
}

function sessionPath(userId: string, environment?: SaxoEnvironment): string {
  const suffix = environment ? `.${environment}` : "";
  return path.join(vaultDir(), `${userId}${suffix}.json`);
}

function portfolioPath(userId: string, environment?: SaxoEnvironment): string {
  const suffix = environment ? `.${environment}` : "";
  return path.join(webRoot(), ".local", "saxo-portfolio", `${userId}${suffix}.json`);
}

export async function writeSaxoSession(
  userId: string,
  environment: SaxoEnvironment,
  tokens: SaxoTokens,
  encryptionKey: Buffer,
  nowMs: number,
): Promise<void> {
  const dir = vaultDir();
  await mkdir(dir, { recursive: true });
  const stored: StoredSession = {
    userId,
    environment,
    accessToken: tokens.accessToken,
    refreshToken: tokens.refreshToken,
    accessExpiresAt: nowMs + tokens.expiresIn * 1000,
    refreshExpiresAt: nowMs + tokens.refreshExpiresIn * 1000,
  };
  const payload = encryptJson(stored, encryptionKey);
  await writeFile(sessionPath(userId, environment), payload, { encoding: "utf8", mode: 0o600 });
  if (environment === "live") {
    await writeFile(sessionPath(userId), payload, { encoding: "utf8", mode: 0o600 });
  }
}

async function readStoredSession(
  userId: string,
  environment: SaxoEnvironment,
  file: string,
  encryptionKey: Buffer,
  nowMs: number,
): Promise<StoredSession | null> {
  try {
    const decrypted = decryptJson(await readFile(file, "utf8"), encryptionKey);
    if (!decrypted || typeof decrypted !== "object") return null;
    const parsed = decrypted as StoredSession;
    if (parsed.userId !== userId || parsed.environment !== environment) return null;
    if (parsed.refreshExpiresAt <= nowMs) return null;
    if (!parsed.accessToken || !parsed.refreshToken) return null;
    return parsed;
  } catch {
    return null;
  }
}

type SessionClock = { accessExpiresAt: number; refreshExpiresAt: number };

async function probeSessionClock(
  userId: string,
  environment: SaxoEnvironment,
  file: string,
  encryptionKey: Buffer,
): Promise<{ status: "ok"; clock: SessionClock } | { status: "absent" } | { status: "unreadable" }> {
  try {
    const decrypted = decryptJson(await readFile(file, "utf8"), encryptionKey);
    if (!decrypted || typeof decrypted !== "object") return { status: "unreadable" };
    const parsed = decrypted as StoredSession;
    if (parsed.userId !== userId || parsed.environment !== environment) return { status: "unreadable" };
    if (!parsed.accessToken || !parsed.refreshToken) return { status: "unreadable" };
    return {
      status: "ok",
      clock: { accessExpiresAt: parsed.accessExpiresAt, refreshExpiresAt: parsed.refreshExpiresAt },
    };
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") return { status: "absent" };
    return { status: "unreadable" };
  }
}

/** Reports whether a saved Saxo sign-in can still be used. Tokens stay on the server. */
export async function readSaxoLinkState(
  userId: string,
  environment: SaxoEnvironment,
  encryptionKey: Buffer,
  nowMs: number,
): Promise<SaxoLinkState> {
  const specific = await probeSessionClock(userId, environment, sessionPath(userId, environment), encryptionKey);
  const chosen = specific.status === "absent" ? await probeSessionClock(userId, environment, sessionPath(userId), encryptionKey) : specific;
  if (chosen.status === "absent") return "absent";
  if (chosen.status === "unreadable") return "unknown";
  return classifySaxoLink(chosen.clock, nowMs);
}

export async function readSaxoSession(
  userId: string,
  environment: SaxoEnvironment,
  encryptionKey: Buffer,
  nowMs: number,
): Promise<StoredSession | null> {
  const specific = await readStoredSession(userId, environment, sessionPath(userId, environment), encryptionKey, nowMs);
  if (specific) return specific;
  return readStoredSession(userId, environment, sessionPath(userId), encryptionKey, nowMs);
}

export async function writeBrokerPortfolio(userId: string, portfolio: BrokerPortfolioView): Promise<void> {
  const body = JSON.stringify({ userId, portfolio });
  const dir = path.dirname(portfolioPath(userId, portfolio.environment));
  await mkdir(dir, { recursive: true });
  await writeFile(portfolioPath(userId, portfolio.environment), body, { encoding: "utf8", mode: 0o600 });
  if (portfolio.environment === "live") {
    await writeFile(portfolioPath(userId), body, { encoding: "utf8", mode: 0o600 });
  }
}

async function readPortfolioFile(userId: string, file: string): Promise<BrokerPortfolioView | null> {
  try {
    const parsed = JSON.parse(await readFile(file, "utf8")) as {
      userId?: string;
      portfolio?: BrokerPortfolioView;
    };
    if (parsed.userId !== userId || !parsed.portfolio) return null;
    if (parsed.portfolio.environment !== "live" && parsed.portfolio.environment !== "simulation") return null;
    return repairStoredPortfolio(parsed.portfolio);
  } catch {
    return null;
  }
}

/** Live wealth wins. A simulation file is returned only when no live snapshot exists. */
export async function readBrokerPortfolio(userId: string): Promise<BrokerPortfolioView | null> {
  const live = await readPortfolioFile(userId, portfolioPath(userId, "live"));
  if (live?.environment === "live") return live;
  const legacy = await readPortfolioFile(userId, portfolioPath(userId));
  if (legacy?.environment === "live") return legacy;
  const simulation = await readPortfolioFile(userId, portfolioPath(userId, "simulation"));
  if (simulation?.environment === "simulation") return simulation;
  return legacy?.environment === "simulation" ? legacy : null;
}

export function saxoArtifactDir(): string {
  return path.join(webRoot(), ".local", "saxo-discovery");
}
