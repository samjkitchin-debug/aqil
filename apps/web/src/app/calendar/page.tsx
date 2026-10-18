import { Suspense } from "react";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import { ForwardHorizonSection } from "@/components/forward/forward-horizon-section";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { loadForwardHorizonBundle } from "@/lib/forward/load-forward-horizon";

async function CalendarBody() {
  const loaded = await loadForwardHorizonBundle();
  if (loaded.status === "ok") {
    return <ForwardHorizonSection bundle={loaded.bundle} source={loaded.source} />;
  }
  const reason =
    loaded.status === "unauthorized"
      ? "unauthorized"
      : loaded.status === "invalid"
        ? "invalid"
        : "missing";
  return <ResearchEmptyState reason={reason} />;
}

export default function CalendarPage() {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/calendar">
      <p className="research-body mb-[var(--space-4)]">
        Upcoming catalysts for the vetted ETF universe, over the next 30–90 days. Filter
        controls will expand as coverage grows.
      </p>
      <Suspense fallback={<ResearchEmptyState reason="missing" />}>
        <CalendarBody />
      </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
