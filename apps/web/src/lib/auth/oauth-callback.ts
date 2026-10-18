import { safeNextPath } from "./safe-next.ts";

export type CallbackInput = {
  requestOrigin: string;
  configuredOrigin: string | null;
  providerError: string | null;
  code: string | null;
  next: string | null;
  exchangeOk: boolean;
};

/** Decides the post-OAuth redirect without logging codes or tokens. */
export function oauthCallbackDestination(input: CallbackInput): string {
  const login = (reason: string) => {
    const base = input.configuredOrigin ?? input.requestOrigin;
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
