import "server-only";

import { cookies } from "next/headers";

const FOUNDER_COOKIE = "aqil_founder_insight";

export function researchFixtureFallbackAllowed(): boolean {
  if (process.env.NODE_ENV === "production") {
    return false;
  }
  return process.env.AQIL_ALLOW_RESEARCH_FIXTURE === "true";
}

/** Server-side gate for unpublished founder research (not UI labels). */
export async function isFounderResearchAuthorised(): Promise<boolean> {
  const token = process.env.AQIL_FOUNDER_INSIGHT_TOKEN?.trim();
  if (!token) {
    return process.env.NODE_ENV !== "production";
  }
  const jar = await cookies();
  return jar.get(FOUNDER_COOKIE)?.value === token;
}
