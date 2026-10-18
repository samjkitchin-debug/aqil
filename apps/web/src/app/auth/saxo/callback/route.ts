import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { resolveAccess } from "@/lib/auth/access";
import { readSaxoConnectionEnv } from "@/lib/saxo/sim-env";
import { requestSaxoToken } from "@/lib/saxo/sim-http";
import { SAXO_STATE_COOKIE, openSaxoState, saxoConnectAllowed, type SaxoEnvironment } from "@/lib/saxo/sim-guard";
import { writeSaxoSession } from "@/lib/saxo/sim-session";
import { syncSaxoPortfolio } from "@/lib/saxo/sim-sync";

function fail(origin: string, reason: string) {
  const response = NextResponse.redirect(new URL(`/my-wealth?error=${reason}`, origin));
  response.headers.set("Cache-Control", "private, no-store");
  response.cookies.set(SAXO_STATE_COOKIE, "", { path: "/auth/saxo", maxAge: 0 });
  return response;
}

function environmentPrefix(value: string | undefined): SaxoEnvironment | null {
  if (value === "live" || value === "simulation") return value;
  return null;
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  if (url.searchParams.get("error")) return fail(url.origin, "saxo_denied");

  const cookieStore = await cookies();
  const packed = cookieStore.get(SAXO_STATE_COOKIE)?.value ?? "";
  const separator = packed.indexOf(".");
  const environment = environmentPrefix(packed.slice(0, separator));
  const sealed = separator > 0 ? packed.slice(separator + 1) : "";
  if (!environment) return fail(url.origin, "saxo_state");

  const env = readSaxoConnectionEnv(environment);
  if (
    !env.ok ||
    !saxoConnectAllowed({
      environment,
      nodeEnv: process.env.NODE_ENV,
      requestHost: url.host,
      redirectUri: env.redirectUri,
    })
  ) {
    return fail(url.origin, "saxo_unavailable");
  }

  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const opened = sealed ? openSaxoState(sealed, env.appSecret, Date.now()) : null;
  if (!code || !state || !opened || opened.state !== state || opened.environment !== environment) {
    return fail(url.origin, "saxo_state");
  }

  const access = await resolveAccess();
  if (access.status !== "authenticated_authorised" || access.userId !== opened.userId) {
    return fail(url.origin, "saxo_user");
  }

  const exchanged = await requestSaxoToken(
    {
      grant: "authorization_code",
      environment,
      code,
      appKey: env.appKey,
      appSecret: env.appSecret,
      redirectUri: env.redirectUri,
    },
    fetch,
  );
  if (!exchanged.ok) return fail(url.origin, "saxo_exchange");

  const now = Date.now();
  await writeSaxoSession(access.userId, environment, exchanged.tokens, env.encryptionKey, now);
  const synced = await syncSaxoPortfolio({
    userId: access.userId,
    environment,
    appKey: env.appKey,
    appSecret: env.appSecret,
    redirectUri: env.redirectUri,
    encryptionKey: env.encryptionKey,
    nowMs: now,
  });
  const response = NextResponse.redirect(
    new URL(synced === "ok" ? "/my-wealth" : `/my-wealth?error=${synced}`, url.origin),
  );
  response.headers.set("Cache-Control", "private, no-store");
  response.cookies.set(SAXO_STATE_COOKIE, "", { path: "/auth/saxo", maxAge: 0 });
  return response;
}
