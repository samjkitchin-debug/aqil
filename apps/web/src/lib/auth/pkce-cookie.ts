export type AuthCookie = {
  name: string;
  value: string;
  options?: Record<string, unknown>;
};

type CookieTarget = {
  set: (name: string, value: string, options?: Record<string, unknown>) => void;
};

/** Writes every auth cookie onto one response. A later redirect must be that same response. */
export function applyAuthCookies(target: CookieTarget, cookiesToSet: readonly AuthCookie[]): void {
  for (const cookie of cookiesToSet) {
    target.set(cookie.name, cookie.value, cookie.options);
  }
}

/** True when the browser stored a Supabase PKCE verifier. Values are never inspected. */
export function hasPkceVerifierCookie(names: readonly string[]): boolean {
  return names.some((name) => name.startsWith("sb-") && name.includes("code-verifier"));
}
