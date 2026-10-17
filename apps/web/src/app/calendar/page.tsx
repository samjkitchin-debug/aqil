import { Suspense } from "react";

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
    <AppShell title="Calendar">
      <p className="research-body mb-[var(--space-4)]">
        30–90 day catalyst view for the vetted ETF research universe. Filter controls will
        expand as coverage grows.
      </p>
      <Suspense fallback={<ResearchEmptyState reason="missing" />}>
        <CalendarBody />
      </Suspense>
    </AppShell>
  );
}
