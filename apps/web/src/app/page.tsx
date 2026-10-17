import { AppShell } from "@/components/app-shell";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { ResearchInsightView } from "@/components/research/research-insight-view";
import { loadFounderResearchInsight } from "@/lib/research/load-founder-insight";

export default async function TodayPage() {
  const loaded = await loadFounderResearchInsight();

  return (
    <AppShell title="Today">
      <section aria-labelledby="macro-intelligence-heading">
        <h2 id="macro-intelligence-heading" className="research-section-title">
          Macro intelligence
        </h2>
        {loaded.status === "ok" ? (
          <ResearchInsightView
            insight={loaded.insight}
            source={loaded.source}
            compact
          />
        ) : (
          <ResearchEmptyState reason={loaded.status === "invalid" ? "invalid" : "missing"} />
        )}
      </section>
    </AppShell>
  );
}
