"use server";

import { redirect } from "next/navigation";

import { safeNextPath } from "@/lib/auth/safe-next";
import { configuredAppOrigin, isProviderEnabled } from "@/lib/auth/session-policy";
import { isSupabaseConfigured } from "@/lib/env/public";
import { createSupabaseServerClient } from "@/lib/supabase/server";

function appOrigin(): string | null {
  const resolved = configuredAppOrigin({
    nodeEnv: process.env.NODE_ENV,
    appUrl: process.env.NEXT_PUBLIC_APP_URL,
  });
  return resolved.ok ? resolved.origin : null;
}

export async function signInWithGoogle(formData: FormData): Promise<void> {
  const next = safeNextPath(String(formData.get("next") ?? "/"));
  const origin = appOrigin();
  if (!isSupabaseConfigured() || !origin) {
    redirect("/login?error=unavailable");
  }

  if (!isProviderEnabled("google")) {
    redirect("/login?error=provider_denied");
  }
  const supabase = await createSupabaseServerClient();
  const redirectTo = `${origin}/auth/callback?next=${encodeURIComponent(next)}`;
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo,
      scopes: "openid email profile",
      queryParams: { prompt: "select_account" },
    },
  });

  const target = data.url;
  if (error || !target) {
    redirect("/login?error=provider_denied");
  }
  redirect(target);
}

export async function signOut(): Promise<void> {
  if (isSupabaseConfigured()) {
    const supabase = await createSupabaseServerClient();
    await supabase.auth.signOut({ scope: "local" });
  }
  redirect("/login");
}
