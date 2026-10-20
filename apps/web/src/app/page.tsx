import { Suspense } from "react";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import { ResearchInsightView } from "@/components/research/research-insight-view";
import { SourcedUpdatesPanel } from "@/components/research/sourced-updates-panel";
import { loadFounderResearchInsight } from "@/lib/research/load-founder-insight";
import { loadSourcedUpdates } from "@/lib/research/load-sourced-updates";

async function TodayBriefing() {
  const sourced = await loadSourcedUpdates();
  const updates = sourced.status === "ok" ? sourced.updates : [];

  return <SourcedUpdatesPanel updates={updates} variant="briefing" />;
}

async function SahmPreviewBlock() {
  const loaded = await loadFounderResearchInsight();
  if (loaded.status !== "ok") {
    return null;
  }

  return (
    <section
      aria-labelledby="sahm-preview-heading"
      className="mt-[var(--space-6)]"
      data-testid="sahm-internal-preview"
    >
      <h2 id="sahm-preview-heading" className="research-section-title">
        Internal preview
      </h2>
      <ResearchInsightView insight={loaded.insight} source={loaded.source} compact />
    </section>
  );
}

export default function TodayPage() {
  return (
    <AppShell title="Today">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/">
          <section aria-labelledby="sourced-briefing-heading">
            <h2 id="sourced-briefing-heading" className="research-section-title">
              Sourced briefing
            </h2>
            <Suspense fallback={<p className="research-body">Loading sourced updates…</p>}>
              <TodayBriefing />
            </Suspense>
          </section>
          <Suspense fallback={null}>
            <SahmPreviewBlock />
          </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
