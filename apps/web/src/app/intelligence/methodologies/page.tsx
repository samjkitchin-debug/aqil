import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { MethodologyOverviewSection } from "@/components/intelligence/methodology-overview";

export default function MethodologiesPage() {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/intelligence/methodologies">
          <Suspense fallback={<p className="research-body">Loading methodologies…</p>}>
            <MethodologyOverviewSection />
          </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
