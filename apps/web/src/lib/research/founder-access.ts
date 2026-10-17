import "server-only";

import { cookies, headers } from "next/headers";

const FOUNDER_COOKIE = "aqil_founder_insight";
const FOUNDER_HEADER = "x-aqil-founder-insight";

export function researchFixtureFallbackAllowed(): boolean {
  if (process.env.AQIL_ALLOW_RESEARCH_FIXTURE === "true") {
    return true;
  }
  return process.env.NODE_ENV !== "production";
}

/** Server-side gate for unpublished founder research (not UI labels). */
export async function isFounderResearchAuthorised(): Promise<boolean> {
  const token = process.env.AQIL_FOUNDER_INSIGHT_TOKEN?.trim();
  if (!token) {
    return process.env.NODE_ENV !== "production";
  }
  const jar = await cookies();
  if (jar.get(FOUNDER_COOKIE)?.value === token) {
    return true;
  }
  if (process.env.AQIL_ALLOW_FOUNDER_INSIGHT_HEADER === "true") {
    const header = (await headers()).get(FOUNDER_HEADER);
    return header === token;
  }
  return false;
}
