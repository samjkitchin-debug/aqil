import { Suspense } from "react";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import { EconomicEvidenceBriefing } from "@/components/research/economic-evidence-briefing";
import { EventsAndThemesSection } from "@/components/research/events-and-themes";
import { MacroConditionsSection } from "@/components/research/macro-conditions-panel";
import { loadEconomicEvidence } from "@/lib/research/load-economic-evidence";
import { presentEconomicEvidence } from "@/lib/research/present-economic-evidence";


async function ConditionsDashboard({
  searchParams,
}: {
  searchParams: Promise<{ region?: string }>;
}) {
  const params = await searchParams;
  const loaded = await loadEconomicEvidence();
  const briefing = loaded.status === "ready" ? presentEconomicEvidence(loaded.input) : null;
  const lines = Object.fromEntries((briefing?.seriesLines ?? []).map((line) => [line.sourceId, line.compact]));
  return (
    <>
      {loaded.status === "unavailable" ? (
        <p className="research-body" data-testid="economic-reading-unavailable">
          {loaded.reason}
        </p>
      ) : briefing ? (
        <EconomicEvidenceBriefing view={briefing} />
      ) : null}
      <MacroConditionsSection variant="dashboard" seriesLines={lines} region={params.region} />
    </>
  );
}

export default function ConditionsPage({
  searchParams,
}: {
  searchParams: Promise<{ region?: string }>;
}) {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/conditions">
          <section aria-labelledby="conditions-heading">
            <h2 id="conditions-heading" className="research-section-title">
              Conditions
            </h2>
            <Suspense fallback={<p className="research-body">Loading conditions…</p>}>
              <ConditionsDashboard searchParams={searchParams} />
            </Suspense>
            <Suspense fallback={<p className="research-body">Loading events and themes…</p>}>
              <EventsAndThemesSection variant="compact" />
            </Suspense>
          </section>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
