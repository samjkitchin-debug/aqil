import "server-only";

import { isAllowlisted, parseAuthorisedUserIds } from "@/lib/auth/allowlist";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { isSupabaseConfigured } from "@/lib/env/public";

export type AccessResolution =
  | { status: "signed_out" }
  | { status: "unavailable" }
  | { status: "unauthorised"; userId: string }
  | { status: "authorised"; userId: string };

function isMissingGrantsRelation(error: { code?: string; message?: string }): boolean {
  const code = error.code ?? "";
  const message = (error.message ?? "").toLowerCase();
  return code === "42P01" || code === "PGRST205" || message.includes("access_grants");
}

function isTransportFailure(error: { name?: string; message?: string; status?: number }): boolean {
  if (error.name === "AuthRetryableFetchError") return true;
  if (error.status === 0) return true;
  const message = (error.message ?? "").toLowerCase();
  return message.includes("fetch") || message.includes("network") || message.includes("timeout");
}

/**
 * One verified identity check for this request.
 * Uses auth.getUser(), which asks the Auth server to validate the session.
 * getSession().user is not used for authorisation.
 */
export async function resolveAccess(): Promise<AccessResolution> {
  if (!isSupabaseConfigured()) return { status: "unavailable" };

  try {
    const supabase = await createSupabaseServerClient();
    const { data, error } = await supabase.auth.getUser();
    if (error) {
      if (isTransportFailure(error)) return { status: "unavailable" };
      return { status: "signed_out" };
    }
    if (!data.user) return { status: "signed_out" };

    const userId = data.user.id;
    const allowlist = parseAuthorisedUserIds(process.env.AQIL_AUTHORISED_USER_IDS);
    if (isAllowlisted(userId, allowlist)) {
      return { status: "authorised", userId };
    }

    const grant = await supabase
      .from("access_grants")
      .select("role")
      .eq("user_id", userId)
      .maybeSingle();

    if (grant.error) {
      if (isMissingGrantsRelation(grant.error)) {
        return { status: "unauthorised", userId };
      }
      return { status: "unavailable" };
    }
    if (grant.data?.role === "founder") {
      return { status: "authorised", userId };
    }
    return { status: "unauthorised", userId };
  } catch {
    return { status: "unavailable" };
  }
}
