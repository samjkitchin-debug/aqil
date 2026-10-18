import "server-only";

import { resolveAccess } from "@/lib/auth/access";

export function researchFixtureFallbackAllowed(): boolean {
  if (process.env.NODE_ENV === "production") {
    return false;
  }
  return process.env.AQIL_ALLOW_RESEARCH_FIXTURE === "true";
}

/** Signed-in research pages. This does not grant service-role or worker access. */
export async function isFounderResearchAuthorised(): Promise<boolean> {
  const access = await resolveAccess();
  return access.status === "authenticated_authorised";
}
