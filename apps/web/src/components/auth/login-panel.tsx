"use client";

import { useSearchParams } from "next/navigation";

import { safeNextPath } from "@/lib/auth/safe-next";

const ERRORS: Record<string, string> = {
  signed_out: "Sign in to continue.",
  unavailable: "Authentication is unavailable. Private data has not been shown.",
  session_ended: "Your session ended. Sign in again.",
  provider_denied: "Google sign-in was denied or could not be started.",
  missing_code: "The sign-in response did not include a code.",
  exchange_failed: "The sign-in code could not be exchanged for a session.",
  rejected_redirect: "The sign-in redirect did not match this application.",
};

export function LoginPanel() {
  const params = useSearchParams();
  const nextPath = safeNextPath(params.get("next"));
  const message = ERRORS[params.get("error") ?? ""] ;

  return (
    <section className="max-w-prose" aria-labelledby="page-title">
      <p className="text-muted">
        Aqil uses Google through Supabase Auth. Your Supabase user id is your identity.
      </p>
      {message ? (
        <p className="mt-[var(--space-4)] text-foreground" role="alert" data-testid="login-error">
          {message}
        </p>
      ) : null}
      <form action="/auth/google" method="get" className="mt-[var(--space-6)]">
        <input type="hidden" name="next" value={nextPath} />
        <button type="submit" className="aq-button">
          Continue with Google
        </button>
      </form>
    </section>
  );
}
