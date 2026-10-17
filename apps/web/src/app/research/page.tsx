import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { ResearchInsightView } from "@/components/research/research-insight-view";
import { loadFounderResearchInsight } from "@/lib/research/load-founder-insight";

async function ResearchDetail() {
  const loaded = await loadFounderResearchInsight();

  if (loaded.status === "ok") {
    return (
      <ResearchInsightView insight={loaded.insight} source={loaded.source} />
    );
  }

  return (
    <ResearchEmptyState
      reason={loaded.status === "invalid" ? "invalid" : "missing"}
    />
  );
}

export default function ResearchPage() {
  return (
    <AppShell title="Research">
      <Suspense fallback={<ResearchEmptyState reason="missing" />}>
        <ResearchDetail />
      </Suspense>
    </AppShell>
  );
}
