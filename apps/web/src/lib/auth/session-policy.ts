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
  if (
    error.status === 429 ||
    (typeof error.status === "number" && error.status >= 500 && error.status <= 599) ||
    error.name === "AuthRetryableFetchError"
  ) {
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

/** Public pages, including login and the OAuth callback, must not call the Auth server. */
export function shouldContactAuthServer(isPublic: boolean): boolean {
  return !isPublic;
}

/** Supabase session cookies only. Names are checked; values are never read here. */
export function hasAuthSessionCookie(names: readonly string[]): boolean {
  return names.some((name) => name.startsWith("sb-") && name.includes("-auth-token"));
}

/**
 * Deployed environments must name their own origin. Local development may use localhost.
 * This is not an account-linking rule and does not read email addresses.
 */
export function configuredAppOrigin(env: {
  nodeEnv?: string;
  appUrl?: string;
}): { ok: true; origin: string } | { ok: false } {
  const configured = env.appUrl?.trim().replace(/\/$/, "");
  if (configured) {
    try {
      return { ok: true, origin: new URL(configured).origin };
    } catch {
      return { ok: false };
    }
  }
  if (env.nodeEnv === "production") return { ok: false };
  return { ok: true, origin: "http://localhost:3000" };
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
