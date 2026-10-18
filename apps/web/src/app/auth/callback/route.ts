import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { oauthCallbackDestination } from "@/lib/auth/oauth-callback";
import { applyAuthCookies, hasPkceVerifierCookie } from "@/lib/auth/pkce-cookie";
import { configuredAppOrigin } from "@/lib/auth/session-policy";
import { isSupabaseConfigured, requirePublicEnv } from "@/lib/env/public";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const resolved = configuredAppOrigin({
    nodeEnv: process.env.NODE_ENV,
    appUrl: process.env.NEXT_PUBLIC_APP_URL,
  });
  if (!resolved.ok) {
    return NextResponse.redirect(new URL("/login?error=unavailable", url.origin));
  }
  const configuredOrigin = resolved.origin;
  const code = url.searchParams.get("code");
  const providerError = url.searchParams.get("error");
  const originMatches = configuredOrigin === url.origin;
  const exchangeAttempted =
    !providerError && Boolean(code) && isSupabaseConfigured() && originMatches;
  const response = NextResponse.redirect(configuredOrigin);
  response.headers.set("Cache-Control", "private, no-store");

  let exchangeOk = false;
  if (exchangeAttempted && code) {
    const cookieStore = await cookies();
    const supabase = createServerClient(
      requirePublicEnv("NEXT_PUBLIC_SUPABASE_URL"),
      requirePublicEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY"),
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet) {
            applyAuthCookies(response.cookies, cookiesToSet);
          },
        },
      },
    );
    console.info("auth.callback", {
      codePresent: true,
      verifierCookiePresent: hasPkceVerifierCookie(cookieStore.getAll().map((cookie) => cookie.name)),
      originMatches,
      exchangeAttempted: true,
    });
    const result = await supabase.auth.exchangeCodeForSession(code);
    exchangeOk = !result.error;
    console.info("auth.callback.exchange", {
      exchangeAttemptedOnce: true,
      errorName: result.error?.name ?? null,
      errorCode: result.error?.code ?? null,
      errorStatus: result.error?.status ?? null,
      errorMessage: result.error?.message?.slice(0, 180) ?? null,
    });
  }

  const destination = oauthCallbackDestination({
    requestOrigin: url.origin,
    configuredOrigin,
    providerError,
    code,
    next: url.searchParams.get("next"),
    exchangeOk,
  });
  response.headers.set("Location", destination);
  return response;
}
