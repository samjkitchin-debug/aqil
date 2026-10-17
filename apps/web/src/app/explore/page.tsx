import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { ForwardCompanyFilings } from "@/components/forward/forward-company-filings";
import { ForwardEtfExplore } from "@/components/forward/forward-etf-explore";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { loadForwardHorizonBundle } from "@/lib/forward/load-forward-horizon";

async function ExploreForward() {
  const loaded = await loadForwardHorizonBundle();
  if (loaded.status === "ok") {
    return (
      <>
        <ForwardEtfExplore bundle={loaded.bundle} />
        <div className="mt-[var(--space-6)]">
          <ForwardCompanyFilings bundle={loaded.bundle} />
        </div>
      </>
    );
  }
  const reason =
    loaded.status === "unauthorized"
      ? "unauthorized"
      : loaded.status === "invalid"
        ? "invalid"
        : "missing";
  return <ResearchEmptyState reason={reason} />;
}

export default function ExplorePage() {
  return (
    <AppShell title="Explore">
      <h1 className="aq-panel-heading mb-[var(--space-4)] font-semibold text-foreground">
        Explore
      </h1>
      <Suspense fallback={<ResearchEmptyState reason="missing" />}>
        <ExploreForward />
      </Suspense>
    </AppShell>
  );
}
