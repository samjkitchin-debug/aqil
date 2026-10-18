const USER_ID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/** Explicit operator allow-list. An empty value authorises nobody. */
export function parseAuthorisedUserIds(raw: string | undefined): Set<string> {
  if (!raw) return new Set();
  const ids = raw
    .split(",")
    .map((part) => part.trim().toLowerCase())
    .filter((part) => USER_ID.test(part));
  return new Set(ids);
}

export function isAllowlisted(userId: string, allowlist: ReadonlySet<string>): boolean {
  return allowlist.has(userId.toLowerCase());
}

/** Client-supplied ids must never select another owner's rows. */
export function isForeignUserId(requested: string | null | undefined, verifiedUserId: string): boolean {
  if (!requested) return false;
  return requested.toLowerCase() !== verifiedUserId.toLowerCase();
}
