import "server-only";

import { cache } from "react";

import { isAllowlisted, parseAuthorisedUserIds } from "@/lib/auth/allowlist";
import { classifyAuthFailure, type AccessStatus } from "@/lib/auth/session-policy";
import { isSupabaseConfigured } from "@/lib/env/public";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export type AccessResolution =
  | { status: "signed_out" }
  | { status: "temporarily_unavailable" }
  | { status: "terminal_invalid_session" }
  | { status: "authenticated_denied"; userId: string }
  | { status: "authenticated_authorised"; userId: string };

function rethrowRedirect(error: unknown): void {
  if (
    typeof error === "object" &&
    error !== null &&
    "digest" in error &&
    String((error as { digest?: unknown }).digest).startsWith("NEXT_REDIRECT")
  ) {
    throw error;
  }
}

function isMissingGrantsRelation(error: { code?: string; message?: string }): boolean {
  const code = error.code ?? "";
  const message = (error.message ?? "").toLowerCase();
  return code === "42P01" || code === "PGRST205" || message.includes("access_grants");
}

async function resolveAccessOnce(): Promise<AccessResolution> {
  if (!isSupabaseConfigured()) return { status: "temporarily_unavailable" };

  try {
    const supabase = await createSupabaseServerClient();
    const { data, error } = await supabase.auth.getUser();
    if (error || !data.user) {
      const status = classifyAuthFailure(error);
      if (status === "temporarily_unavailable" || status === "terminal_invalid_session") {
        return { status };
      }
      return { status: "signed_out" };
    }

    const userId = data.user.id;
    const allowlist = parseAuthorisedUserIds(process.env.AQIL_AUTHORISED_USER_IDS);
    if (isAllowlisted(userId, allowlist)) {
      return { status: "authenticated_authorised", userId };
    }

    const grant = await supabase
      .from("access_grants")
      .select("role")
      .eq("user_id", userId)
      .maybeSingle();

    if (grant.error) {
      if (isMissingGrantsRelation(grant.error)) {
        return { status: "authenticated_denied", userId };
      }
      return { status: "temporarily_unavailable" };
    }
    if (grant.data?.role === "founder") {
      return { status: "authenticated_authorised", userId };
    }
    return { status: "authenticated_denied", userId };
  } catch (error) {
    rethrowRedirect(error);
    return { status: "temporarily_unavailable" };
  }
}

/** One Auth server check per React render, shared by every server component in the request. */
export const resolveAccess = cache(resolveAccessOnce);

export type { AccessStatus };
