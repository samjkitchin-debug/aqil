import { Suspense } from "react";
import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { signOut } from "@/lib/auth/actions";
import { resolveAccess } from "@/lib/auth/access";

async function DeniedBody() {
  const access = await resolveAccess();
  if (access.status === "signed_out" || access.status === "unavailable") {
    redirect("/login?error=" + (access.status === "unavailable" ? "unavailable" : "signed_out"));
  }
  if (access.status === "authorised") {
    redirect("/");
  }

  return (
    <section className="max-w-prose" aria-labelledby="denied-heading">
      <h1 id="denied-heading" className="aq-panel-heading font-semibold text-foreground">
        Access denied
      </h1>
      <p className="mt-[var(--space-3)] text-muted" data-testid="access-denied">
        This Google account is not permitted to use Aqil. Your user id is{" "}
        <span className="font-mono">{access.userId}</span>. Ask the operator to grant this id in
        AQIL_AUTHORISED_USER_IDS or in access_grants. No private data is shown.
      </p>
      <form action={signOut} className="mt-[var(--space-6)]">
        <button type="submit" className="text-sm text-muted underline">
          Sign out
        </button>
      </form>
    </section>
  );
}

export default function AccessDeniedPage() {
  return (
    <AppShell title="Access denied">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <DeniedBody />
      </Suspense>
    </AppShell>
  );
}
