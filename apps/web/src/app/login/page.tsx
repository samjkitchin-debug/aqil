import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { LoginPanel } from "@/components/auth/login-panel";

function LoginFallback() {
  return (
    <section className="max-w-prose" aria-labelledby="page-title">
      <p className="text-muted">
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
