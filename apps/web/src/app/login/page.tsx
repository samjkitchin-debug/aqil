import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { LoginPanel } from "@/components/auth/login-panel";

function LoginFallback() {
  return (
    <section className="max-w-prose" aria-labelledby="login-heading">
      <h1 id="login-heading" className="aq-panel-heading font-semibold text-foreground">
        Sign in
      </h1>
      <p className="mt-[var(--space-3)] text-muted">
        Aqil uses Google through Supabase Auth. Your Supabase user id is your identity.
      </p>
    </section>
  );
}

export default function LoginPage() {
  return (
    <AppShell title="Sign in">
      <Suspense fallback={<LoginFallback />}>
        <LoginPanel />
      </Suspense>
    </AppShell>
  );
}
