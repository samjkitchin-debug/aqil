import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { InsightsPanel } from "@/components/intelligence/insights-panel";

export default function InsightsPage() {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/intelligence/insights">
          <InsightsPanel />
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
