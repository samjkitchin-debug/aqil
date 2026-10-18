import "server-only";

import { cache } from "react";

import { classifyAuthFailure, type AccessStatus } from "@/lib/auth/session-policy";
import { isSupabaseConfigured } from "@/lib/env/public";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export type AccessResolution =
  | { status: "signed_out" }
  | { status: "temporarily_unavailable" }
  | { status: "terminal_invalid_session" }
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

    return { status: "authenticated_authorised", userId: data.user.id };
  } catch (error) {
    rethrowRedirect(error);
    return { status: "temporarily_unavailable" };
  }
}

/** One Auth server check per React render, shared by every server component in the request. */
export const resolveAccess = cache(resolveAccessOnce);

export type { AccessStatus };
