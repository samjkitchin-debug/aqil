import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { ResearchHealthSection } from "@/components/intelligence/research-health";

export default function ResearchHealthPage() {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/intelligence/health">
          <Suspense fallback={<p className="research-body">Loading research health…</p>}>
            <ResearchHealthSection />
          </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
