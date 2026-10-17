import { AppShell } from "@/components/app-shell";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { ResearchInsightView } from "@/components/research/research-insight-view";
import { loadFounderResearchInsight } from "@/lib/research/load-founder-insight";

export default async function ResearchPage() {
  const loaded = await loadFounderResearchInsight();

  return (
    <AppShell title="Research">
      {loaded.status === "ok" ? (
        <ResearchInsightView insight={loaded.insight} source={loaded.source} />
      ) : (
        <ResearchEmptyState reason={loaded.status === "invalid" ? "invalid" : "missing"} />
      )}
    </AppShell>
  );
}
