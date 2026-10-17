import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { ResearchInsightView } from "@/components/research/research-insight-view";
import { ForwardHorizonSection } from "@/components/forward/forward-horizon-section";
import { loadForwardHorizonBundle } from "@/lib/forward/load-forward-horizon";
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

  const reason =
    loaded.status === "invalid"
      ? "invalid"
      : loaded.status === "unauthorized"
        ? "unauthorized"
        : "missing";

  return <ResearchEmptyState reason={reason} />;
}

async function HorizonSection() {
  const loaded = await loadForwardHorizonBundle();
  if (loaded.status === "ok") {
    return <ForwardHorizonSection bundle={loaded.bundle} source={loaded.source} compact />;
  }
  return null;
}

export default function TodayPage() {
  return (
    <AppShell title="Today">
      <section aria-labelledby="horizon-heading" className="mb-[var(--space-6)]">
        <h2 id="horizon-heading" className="research-section-title sr-only">
          On the horizon
        </h2>
        <Suspense fallback={null}>
          <HorizonSection />
        </Suspense>
      </section>
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
