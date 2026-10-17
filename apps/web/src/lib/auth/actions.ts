"use server";

import { redirect } from "next/navigation";

import { safeNextPath } from "@/lib/auth/safe-next";
import { isSupabaseConfigured } from "@/lib/env/public";
import { createSupabaseServerClient } from "@/lib/supabase/server";

function appOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_APP_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  return "http://localhost:3000";
}

export async function signInWithGoogle(formData: FormData): Promise<void> {
  const next = safeNextPath(String(formData.get("next") ?? "/"));
  if (!isSupabaseConfigured()) {
    redirect("/login?error=unavailable");
  }

  const supabase = await createSupabaseServerClient();
  const redirectTo = `${appOrigin()}/auth/callback?next=${encodeURIComponent(next)}`;
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
    await supabase.auth.signOut();
  }
  redirect("/login");
}
