import "server-only";

import { saxoEncryptionKey } from "./token-crypto";
import { SAXO_SIM_REDIRECT_URI, type SaxoEnvironment } from "./sim-guard";

const LIVE_LOCAL_REDIRECT = "http://localhost:3000/auth/saxo/callback";

export function readSaxoConnectionEnv(environment: SaxoEnvironment):
  | { ok: true; appKey: string; appSecret: string; redirectUri: string; encryptionKey: Buffer }
  | { ok: false; missing: string[] } {
  const prefix = environment === "live" ? "SAXO_LIVE" : "SAXO_SIM";
  const missing: string[] = [];
  const appKey = process.env[`${prefix}_APP_KEY`]?.trim();
  const appSecret = process.env[`${prefix}_APP_SECRET`]?.trim();
  const redirectUri = process.env[`${prefix}_REDIRECT_URI`]?.trim();
  const encryptionKey = saxoEncryptionKey(process.env.SAXO_TOKEN_ENCRYPTION_KEY);
  if (!appKey) missing.push(`${prefix}_APP_KEY`);
  if (!appSecret) missing.push(`${prefix}_APP_SECRET`);
  if (!redirectUri) missing.push(`${prefix}_REDIRECT_URI`);
  if (!encryptionKey) missing.push("SAXO_TOKEN_ENCRYPTION_KEY");
  const redirectAllowed =
    environment === "simulation" ? redirectUri === SAXO_SIM_REDIRECT_URI : redirectUri === LIVE_LOCAL_REDIRECT;
  if (redirectUri && !redirectAllowed) missing.push(`${prefix}_REDIRECT_URI`);
  if (missing.length > 0 || !appKey || !appSecret || !redirectUri || !encryptionKey) {
    return { ok: false, missing };
  }
  return { ok: true, appKey, appSecret, redirectUri, encryptionKey };
}

export function readSaxoSimEnv():
  | { ok: true; appKey: string; appSecret: string; redirectUri: string }
  | { ok: false } {
  const env = readSaxoConnectionEnv("simulation");
  if (!env.ok) return { ok: false };
  return { ok: true, appKey: env.appKey, appSecret: env.appSecret, redirectUri: env.redirectUri };
}
