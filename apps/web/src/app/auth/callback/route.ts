import { NextResponse } from "next/server";

import { oauthCallbackDestination } from "@/lib/auth/oauth-callback";
import { configuredAppOrigin } from "@/lib/auth/session-policy";
import { isSupabaseConfigured } from "@/lib/env/public";
import { createSupabaseServerClient } from "@/lib/supabase/server";

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

  let exchangeOk = false;
  const code = url.searchParams.get("code");
  const providerError = url.searchParams.get("error");
  if (
    resolved.ok &&
    !providerError &&
    code &&
    isSupabaseConfigured() &&
    configuredOrigin === url.origin
  ) {
    const supabase = await createSupabaseServerClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    exchangeOk = !error;
  }

  const destination = oauthCallbackDestination({
    requestOrigin: url.origin,
    configuredOrigin,
    providerError,
    code,
    next: url.searchParams.get("next"),
    exchangeOk,
  });

  return NextResponse.redirect(destination);
}
