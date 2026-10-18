import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { callbackOrigin, oauthCallbackUrl, oauthRedirectStaysOnOrigin } from "@/lib/auth/oauth-callback";
import { applyAuthCookies } from "@/lib/auth/pkce-cookie";
import { safeNextPath } from "@/lib/auth/safe-next";
import { configuredAppOrigin, isProviderEnabled } from "@/lib/auth/session-policy";
import { isSupabaseConfigured, requirePublicEnv } from "@/lib/env/public";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const resolved = configuredAppOrigin({
    nodeEnv: process.env.NODE_ENV,
    appUrl: process.env.NEXT_PUBLIC_APP_URL,
  });
  const origin = resolved.ok ? resolved.origin : url.origin;
  if (!resolved.ok || resolved.origin !== url.origin || !isSupabaseConfigured()) {
    const stay = callbackOrigin(url.origin, resolved.ok ? resolved.origin : null);
    return NextResponse.redirect(`${stay}/login?error=unavailable`);
  }
  if (!isProviderEnabled("google")) {
    return NextResponse.redirect(`${origin}/login?error=provider_denied`);
  }

  const next = safeNextPath(url.searchParams.get("next"));
  const redirectTo = oauthCallbackUrl(origin);
  const response = NextResponse.redirect(origin);
  response.headers.set("Cache-Control", "private, no-store");
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
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo,
      skipBrowserRedirect: true,
      scopes: "openid email profile",
      queryParams: { prompt: "select_account" },
    },
  });
  if (error || !data.url || !oauthRedirectStaysOnOrigin(data.url, origin)) {
    return NextResponse.redirect(`${origin}/login?error=rejected_redirect`);
  }
  response.cookies.set("aqil-auth-next", next, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
    secure: origin.startsWith("https://"),
    maxAge: 600,
  });
  response.headers.set("Location", data.url);
  return response;
}
