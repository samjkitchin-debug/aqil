export type SaxoLinkState = "active" | "refreshable" | "expired" | "absent" | "unknown";

/** Classifies a decrypted session clock. Unknown means the file could not be read. */
export function classifySaxoLink(
  session: { accessExpiresAt: number; refreshExpiresAt: number } | null,
  nowMs: number,
): Exclude<SaxoLinkState, "unknown"> {
  if (!session) return "absent";
  if (session.refreshExpiresAt <= nowMs) return "expired";
  if (session.accessExpiresAt <= nowMs) return "refreshable";
  return "active";
}
