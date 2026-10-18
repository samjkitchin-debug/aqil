import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

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
    return NextResponse.redirect(`${origin}/login?error=unavailable`);
  }
  if (!isProviderEnabled("google")) {
    return NextResponse.redirect(`${origin}/login?error=provider_denied`);
  }

  const next = safeNextPath(url.searchParams.get("next"));
  const redirectTo = `${origin}/auth/callback?next=${encodeURIComponent(next)}`;
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
  if (error || !data.url) {
    return NextResponse.redirect(`${origin}/login?error=provider_denied`);
  }
  response.headers.set("Location", data.url);
  return response;
}
