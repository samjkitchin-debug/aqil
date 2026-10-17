export type AccessStatus =
  | "authenticated_authorised"
  | "authenticated_denied"
  | "signed_out"
  | "temporarily_unavailable"
  | "terminal_invalid_session";

export type AuthFailure = {
  name?: string;
  message?: string;
  status?: number;
};

const ENABLED = ["google"] as const;

export type EnabledAuthProvider = (typeof ENABLED)[number];

/** Future providers stay disabled until a deliberate product change. */
export function isProviderEnabled(provider: string): provider is EnabledAuthProvider {
  return (ENABLED as readonly string[]).includes(provider);
}

export function classifyAuthFailure(error: AuthFailure | null): AccessStatus {
  if (!error) return "signed_out";
  if (error.status === 429 || error.name === "AuthRetryableFetchError") {
    return "temporarily_unavailable";
  }
  const message = (error.message ?? "").toLowerCase();
  if (
    message.includes("fetch") ||
    message.includes("network") ||
    message.includes("timeout") ||
    message.includes("rate limit")
  ) {
    return "temporarily_unavailable";
  }
  if (
    message.includes("refresh") &&
    (message.includes("already used") ||
      message.includes("not found") ||
      message.includes("invalid") ||
      message.includes("revoked"))
  ) {
    return "terminal_invalid_session";
  }
  if (error.status === 401 || error.status === 403) return "terminal_invalid_session";
  return "signed_out";
}

/** Public pages must not call the Auth server. That avoids refresh storms while signed out. */
export function shouldContactAuthServer(isPublic: boolean): boolean {
  return !isPublic;
}

export function isPrefetchRequest(headers: { get(name: string): string | null }): boolean {
  return (
    headers.get("next-router-prefetch") === "1" ||
    headers.get("purpose") === "prefetch" ||
    headers.get("sec-purpose") === "prefetch"
  );
}

/**
 * HTML documents must not be marked no-store. Next's dev client treats that as
 * immediately stale and reloads the document. Dynamic rendering already opts
 * private routes out of the static cache.
 */
export function documentCacheControl(): null {
  return null;
}
