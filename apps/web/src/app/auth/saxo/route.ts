import { NextResponse } from "next/server";

import { resolveAccess } from "@/lib/auth/access";
import { readSaxoConnectionEnv } from "@/lib/saxo/sim-env";
import {
  SAXO_STATE_COOKIE,
  createSaxoState,
  saxoAuthorizeUrl,
  saxoConnectAllowed,
  sealSaxoState,
  type SaxoEnvironment,
} from "@/lib/saxo/sim-guard";

function environmentFrom(request: Request): SaxoEnvironment {
  const value = new URL(request.url).searchParams.get("environment");
  return value === "simulation" ? "simulation" : "live";
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const environment = environmentFrom(request);
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
    return NextResponse.redirect(new URL("/my-wealth?error=saxo_unavailable", url.origin));
  }

  const access = await resolveAccess();
  if (access.status !== "authenticated_authorised") {
    return NextResponse.redirect(new URL("/login?error=signed_out&next=%2Fmy-wealth", url.origin));
  }

  const state = createSaxoState();
  const sealed = sealSaxoState(
    { state, userId: access.userId, environment, exp: Date.now() + 10 * 60 * 1000 },
    env.appSecret,
  );
  const response = NextResponse.redirect(
    saxoAuthorizeUrl({
      environment,
      appKey: env.appKey,
      state,
      redirectUri: env.redirectUri,
    }),
  );
  response.headers.set("Cache-Control", "private, no-store");
  response.cookies.set(SAXO_STATE_COOKIE, `${environment}.${sealed}`, {
    httpOnly: true,
    sameSite: "lax",
    secure: url.protocol === "https:",
    path: "/auth/saxo",
    maxAge: 600,
  });
  return response;
}
