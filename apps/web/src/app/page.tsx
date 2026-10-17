import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { ResearchInsightView } from "@/components/research/research-insight-view";
import { loadFounderResearchInsight } from "@/lib/research/load-founder-insight";

async function MacroIntelligenceSection() {
  const loaded = await loadFounderResearchInsight();

  if (loaded.status === "ok") {
    return (
      <ResearchInsightView
        insight={loaded.insight}
        source={loaded.source}
        compact
      />
    );
  }

  return (
    <ResearchEmptyState
      reason={loaded.status === "invalid" ? "invalid" : "missing"}
    />
  );
}

export default function TodayPage() {
  return (
    <AppShell title="Today">
      <section aria-labelledby="macro-intelligence-heading">
        <h2 id="macro-intelligence-heading" className="research-section-title">
          Macro intelligence
        </h2>
        <Suspense
          fallback={
            <ResearchEmptyState reason="missing" />
          }
        >
          <MacroIntelligenceSection />
        </Suspense>
      </section>
    </AppShell>
  );
}
