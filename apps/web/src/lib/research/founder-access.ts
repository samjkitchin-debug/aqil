import "server-only";

import { resolveAccess } from "@/lib/auth/access";

export function researchFixtureFallbackAllowed(): boolean {
  if (process.env.NODE_ENV === "production") {
    return false;
  }
  return process.env.AQIL_ALLOW_RESEARCH_FIXTURE === "true";
}

/**
 * Private research is visible only to an explicitly authorised Supabase user.
 * The previous founder cookie and non-production open gate have been removed.
 */
export async function isFounderResearchAuthorised(): Promise<boolean> {
  const access = await resolveAccess();
  return access.status === "authenticated_authorised";
}
