import { Suspense } from "react";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { ResearchInsightView } from "@/components/research/research-insight-view";
import { SloosReadingPanel } from "@/components/research/sloos-reading-panel";
import { SourcedUpdatesPanel } from "@/components/research/sourced-updates-panel";
import { loadFounderResearchInsight } from "@/lib/research/load-founder-insight";
import { loadSloosReading } from "@/lib/research/load-sloos-reading";
import { loadSourcedUpdates } from "@/lib/research/load-sourced-updates";

async function ResearchEvidence() {
  const sourced = await loadSourcedUpdates();
  const updates = sourced.status === "ok" ? sourced.updates : [];
  const loaded = await loadFounderResearchInsight();
  const credit = await loadSloosReading();

  if (loaded.status === "unauthorized") {
    return <ResearchEmptyState reason="unauthorized" />;
  }

  return (
    <>
      <section aria-labelledby="sourced-evidence-heading">
        <h2 id="sourced-evidence-heading" className="research-section-title">
          Sourced facts
        </h2>
        <SourcedUpdatesPanel updates={updates} variant="evidence" />
      </section>
      {credit.status === "ready" ? (
        <div className="mt-[var(--space-6)]">
          <SloosReadingPanel reading={credit.reading} />
        </div>
      ) : null}
      {credit.status === "unavailable" ? (
        <section className="mt-[var(--space-6)]" aria-labelledby="credit-standards-heading">
          <h2 id="credit-standards-heading" className="research-section-title">
            Business credit standards
          </h2>
          <p className="research-body" data-testid="credit-standards-unavailable">
            This reading is unavailable. {credit.reason} Publication remains closed.
          </p>
        </section>
      ) : null}
      {loaded.status === "ok" ? (
        <section
          aria-labelledby="internal-preview-heading"
          className="mt-[var(--space-6)]"
          data-testid="research-internal-preview"
        >
          <h2 id="internal-preview-heading" className="research-section-title">
            Internal preview
          </h2>
          <ResearchInsightView insight={loaded.insight} source={loaded.source} />
        </section>
      ) : null}
    </>
  );
}

export default function ResearchPage() {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/research">
          <Suspense fallback={<p className="research-body">Loading evidence…</p>}>
            <ResearchEvidence />
          </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
