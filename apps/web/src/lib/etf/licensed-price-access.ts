import type { ResearchAuthorisation } from "@/lib/auth/session-policy";

/** Licensed vendor prices. Ordinary Google sign-in is not this claim. */
export const LICENSED_PRICE_WITHHELD =
  "Licensed prices are limited to the founder session. Ordinary sign-in is not enough.";

export function licensedEtfPricesAllowed(authorisation: ResearchAuthorisation): boolean {
  return authorisation === "founder";
}
