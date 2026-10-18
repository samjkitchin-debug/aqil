import { Suspense } from "react";
import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { resolveAccess } from "@/lib/auth/access";

async function AccessDeniedRedirect(): Promise<React.ReactNode> {
  const access = await resolveAccess();
  if (access.status === "authenticated_authorised") {
    redirect("/");
  }
  const reason =
    access.status === "terminal_invalid_session"
      ? "session_ended"
      : access.status === "temporarily_unavailable"
        ? "unavailable"
        : "signed_out";
  redirect(`/login?error=${reason}`);
  return null;
}

export default function AccessDeniedPage() {
  return (
    <AppShell title="Access denied">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <AccessDeniedRedirect />
      </Suspense>
    </AppShell>
  );
}
