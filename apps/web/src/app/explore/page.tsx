import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { ForwardEtfExplore } from "@/components/forward/forward-etf-explore";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { loadForwardHorizonBundle } from "@/lib/forward/load-forward-horizon";

async function ExploreForward() {
  const loaded = await loadForwardHorizonBundle();
  if (loaded.status === "ok") {
    return <ForwardEtfExplore bundle={loaded.bundle} />;
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
      <Suspense fallback={<ResearchEmptyState reason="missing" />}>
        <ExploreForward />
      </Suspense>
    </AppShell>
  );
}
