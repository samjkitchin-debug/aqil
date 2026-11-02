import "server-only";

import { resolveAccess } from "@/lib/auth/access";

export function researchFixtureFallbackAllowed(): boolean {
  if (process.env.NODE_ENV === "production") {
    return false;
  }
  return process.env.AQIL_ALLOW_RESEARCH_FIXTURE === "true";
}

/** Unpublished research. A signed-in account without the founder claim is refused. */
export async function isFounderResearchAuthorised(): Promise<boolean> {
  const access = await resolveAccess();
  return access.status === "authenticated_authorised" && access.researchAuthorisation === "founder";
}
