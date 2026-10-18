import { safeNextPath } from "./safe-next.ts";

export type CallbackInput = {
  requestOrigin: string;
  configuredOrigin: string | null;
  providerError: string | null;
  code: string | null;
  next: string | null;
  exchangeOk: boolean;
};

/**
 * Error redirects stay on the request origin during local development.
 * A configured production or obsolete host must not replace localhost.
 */
export function callbackOrigin(requestOrigin: string, configuredOrigin: string | null): string {
  if (!configuredOrigin || configuredOrigin === requestOrigin) return requestOrigin;
  try {
    const host = new URL(requestOrigin).hostname;
    if (host === "localhost" || host === "127.0.0.1") return new URL(requestOrigin).origin;
  } catch {
    return configuredOrigin;
  }
  return configuredOrigin;
}

/** Exact callback URL. A query string is not part of the allow-listed address. */
export function oauthCallbackUrl(origin: string): string {
  const parsed = new URL(origin);
  return `${parsed.origin}/auth/callback`;
}

/** The provider redirect must return to the same origin that started sign-in. */
export function oauthRedirectStaysOnOrigin(authorizeUrl: string, origin: string): boolean {
  try {
    const redirectTo = new URL(authorizeUrl).searchParams.get("redirect_to");
    if (!redirectTo) return false;
    return new URL(redirectTo).origin === new URL(origin).origin;
  } catch {
    return false;
  }
}

/** Decides the post-OAuth redirect without logging codes or tokens. */
export function oauthCallbackDestination(input: CallbackInput): string {
  const login = (reason: string) => {
    const base = callbackOrigin(input.requestOrigin, input.configuredOrigin);
    return `${base}/login?error=${reason}`;
  };

  if (input.configuredOrigin && input.configuredOrigin !== input.requestOrigin) {
    return login("rejected_redirect");
  }
  if (input.providerError) return login("provider_denied");
  if (!input.code) return login("missing_code");
  if (!input.exchangeOk) return login("exchange_failed");
  const next = safeNextPath(input.next);
  return `${input.requestOrigin}${next}`;
}
