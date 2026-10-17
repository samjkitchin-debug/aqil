export type AccessStatus =
  | "authenticated_authorised"
  | "authenticated_denied"
  | "signed_out"
  | "temporarily_unavailable"
  | "terminal_invalid_session";

export type AuthFailure = {
  name?: string;
  code?: string;
  message?: string;
  status?: number;
};

const ENABLED = ["google"] as const;

export type EnabledAuthProvider = (typeof ENABLED)[number];

/** Future providers stay disabled until a deliberate product change. */
export function isProviderEnabled(provider: string): provider is EnabledAuthProvider {
  return (ENABLED as readonly string[]).includes(provider);
}

const TERMINAL_REFRESH_CODES = new Set([
  "refresh_token_not_found",
  "refresh_token_already_used",
  "session_not_found",
]);

/**
 * 429 and 5xx are temporary. A confirmed dead refresh token is terminal.
 * A bare 401 or 403 is neither: it must not clear every session and it is not proof the Auth service is down.
 */
export function classifyAuthFailure(error: AuthFailure | null): AccessStatus {
  if (!error) return "signed_out";
  const message = (error.message ?? "").toLowerCase();
  const code = (error.code ?? "").toLowerCase();
  if (
    error.status === 429 ||
    (typeof error.status === "number" && error.status >= 500 && error.status <= 599) ||
    error.name === "AuthRetryableFetchError" ||
    message.includes("fetch") ||
    message.includes("network") ||
    message.includes("timeout") ||
    message.includes("rate limit")
  ) {
    return "temporarily_unavailable";
  }
  if (
    TERMINAL_REFRESH_CODES.has(code) ||
    (message.includes("refresh") &&
      (message.includes("already used") || message.includes("not found") || message.includes("revoked")))
  ) {
    return "terminal_invalid_session";
  }
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

/**
 * Next.js 16 prefetch uses `next-router-prefetch` or `next-router-segment-prefetch`.
 * A real navigation sets `sec-fetch-mode: navigate` or `rsc` without those headers.
 * Server Actions set `next-action` and must reach the action.
 */
export function isPrefetchRequest(headers: { get(name: string): string | null }): boolean {
  if (headers.get("next-action")) return false;
  if (headers.get("sec-fetch-mode") === "navigate") return false;
  const nextPrefetch =
    headers.get("next-router-prefetch") === "1" || headers.get("next-router-segment-prefetch") === "1";
  const purpose = `${headers.get("purpose") ?? ""} ${headers.get("sec-purpose") ?? ""}`.toLowerCase();
  const browserPrefetch = purpose.includes("prefetch");
  if (!nextPrefetch && !browserPrefetch) return false;
  if (headers.get("rsc") === "1" && !nextPrefetch) return false;
  return true;
}

/** Auth helpers do not set document cache policy. Private routes set it in next.config.ts. */
export function documentCacheControl(): null {
  return null;
}
