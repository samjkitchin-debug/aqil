import { NextResponse } from "next/server";

import { oauthCallbackDestination } from "@/lib/auth/oauth-callback";
import { isSupabaseConfigured } from "@/lib/env/public";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const configured = process.env.NEXT_PUBLIC_APP_URL?.trim().replace(/\/$/, "") ?? null;
  const configuredOrigin = configured ? new URL(configured).origin : null;

  let exchangeOk = false;
  const code = url.searchParams.get("code");
  const providerError = url.searchParams.get("error");
  if (!providerError && code && isSupabaseConfigured() && (!configuredOrigin || configuredOrigin === url.origin)) {
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
