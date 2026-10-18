import { NextResponse } from "next/server";

import { resolveAccess } from "@/lib/auth/access";
import { readSaxoConnectionEnv } from "@/lib/saxo/sim-env";
import { saxoConnectAllowed } from "@/lib/saxo/sim-guard";
import { readSaxoSession } from "@/lib/saxo/sim-session";
import { syncSaxoPortfolio } from "@/lib/saxo/sim-sync";
import { saxoEncryptionKey } from "@/lib/saxo/token-crypto";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const access = await resolveAccess();
  if (access.status !== "authenticated_authorised") {
    return NextResponse.redirect(new URL("/login?error=signed_out&next=%2Fmy-wealth", url.origin));
  }

  const encryptionKey = saxoEncryptionKey(process.env.SAXO_TOKEN_ENCRYPTION_KEY);
  const now = Date.now();
  const session = encryptionKey
    ? (await readSaxoSession(access.userId, "live", encryptionKey, now)) ??
      (await readSaxoSession(access.userId, "simulation", encryptionKey, now))
    : null;
  if (!session) return NextResponse.redirect(new URL("/my-wealth?error=no_session", url.origin));

  const env = readSaxoConnectionEnv(session.environment);
  if (
    !env.ok ||
    !saxoConnectAllowed({
      environment: session.environment,
      nodeEnv: process.env.NODE_ENV,
      requestHost: url.host,
      redirectUri: env.redirectUri,
    })
  ) {
    return NextResponse.redirect(new URL("/my-wealth?error=saxo_unavailable", url.origin));
  }

  const synced = await syncSaxoPortfolio({
    userId: access.userId,
    environment: session.environment,
    appKey: env.appKey,
    appSecret: env.appSecret,
    redirectUri: env.redirectUri,
    encryptionKey: env.encryptionKey,
    nowMs: Date.now(),
  });
  const response = NextResponse.redirect(
    new URL(synced === "ok" ? "/my-wealth" : `/my-wealth?error=${synced}`, url.origin),
  );
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}
