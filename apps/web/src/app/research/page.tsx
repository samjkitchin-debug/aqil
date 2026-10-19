import { Suspense } from "react";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { ResearchStoryView } from "@/components/research/research-story-view";
import { ForwardResearchDetail } from "@/components/forward/forward-research-detail";
import { ResearchInsightView } from "@/components/research/research-insight-view";
import { loadForwardHorizonBundle } from "@/lib/forward/load-forward-horizon";
import { loadFounderResearchInsight } from "@/lib/research/load-founder-insight";

async function ResearchDetail() {
  const loaded = await loadFounderResearchInsight();

  const forward = await loadForwardHorizonBundle();

  if (loaded.status === "ok") {
    return (
      <>
        <ResearchInsightView insight={loaded.insight} source={loaded.source} />
        {forward.status === "ok" && (
          <div className="mt-[var(--space-6)]">
            <h2 className="research-section-title">Forward intelligence</h2>
            <ForwardResearchDetail bundle={forward.bundle} />
          </div>
        )}
      </>
    );
  }

  if (loaded.status === "unauthorized") {
    return <ResearchEmptyState reason="unauthorized" />;
  }

  return <ResearchStoryView />;
}

export default function ResearchPage() {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/research">
      <Suspense fallback={<ResearchEmptyState reason="missing" />}>
        <ResearchDetail />
      </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
