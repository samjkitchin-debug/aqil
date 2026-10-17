import { Suspense } from "react";
import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { signInWithGoogle, signOut } from "@/lib/auth/actions";
import { resolveAccess } from "@/lib/auth/access";
import { safeNextPath } from "@/lib/auth/safe-next";

const ERRORS: Record<string, string> = {
  signed_out: "Sign in to continue.",
  unavailable: "Authentication is unavailable. Private data has not been shown.",
  provider_denied: "Google sign-in was denied or could not be started.",
  missing_code: "The sign-in response did not include a code.",
  exchange_failed: "The sign-in code could not be exchanged for a session.",
  rejected_redirect: "The sign-in redirect did not match this application.",
};

async function LoginBody({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; next?: string }>;
}) {
  const params = await searchParams;
  const nextPath = safeNextPath(params.next);
  const error = params.error;
  const access = await resolveAccess();
  if (access.status === "authorised") {
    redirect(nextPath);
  }

  const message = error ? ERRORS[error] : undefined;

  return (
    <section className="max-w-prose" aria-labelledby="login-heading">
      <h1 id="login-heading" className="aq-panel-heading font-semibold text-foreground">
        Sign in
      </h1>
      <p className="mt-[var(--space-3)] text-muted">
        Aqil uses Google through Supabase Auth. Signing in does not by itself grant access to
        private research or portfolio data.
      </p>
      {message ? (
        <p className="mt-[var(--space-4)] text-foreground" data-testid="login-error">
          {message}
        </p>
      ) : null}
      {access.status === "unauthorised" ? (
        <p className="mt-[var(--space-4)] text-foreground" data-testid="login-unauthorised">
          This Google account is signed in but is not on the Aqil allow-list. Your user id is{" "}
          <span className="font-mono">{access.userId}</span>. An operator must add that id
          explicitly. The first Google account is never promoted automatically.
        </p>
      ) : null}
      {access.status === "unavailable" ? (
        <p className="mt-[var(--space-4)] text-foreground" data-testid="auth-unavailable">
          The authentication service is not configured or did not respond.
        </p>
      ) : null}
      <form action={signInWithGoogle} className="mt-[var(--space-6)]">
        <input type="hidden" name="next" value={nextPath} />
        <button
          type="submit"
          className="rounded-lg bg-brand-navy px-[var(--space-4)] py-[var(--space-2)] text-inverse"
        >
          Continue with Google
        </button>
      </form>
      {access.status === "unauthorised" ? (
        <form action={signOut} className="mt-[var(--space-4)]">
          <button type="submit" className="text-sm text-muted underline">
            Sign out
          </button>
        </form>
      ) : null}
    </section>
  );
}

export default function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; next?: string }>;
}) {
  return (
    <AppShell title="Sign in">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <LoginBody searchParams={searchParams} />
      </Suspense>
    </AppShell>
  );
}
