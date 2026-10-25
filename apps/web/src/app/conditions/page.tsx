import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { IntelligenceDashboardSection } from "@/components/intelligence/dashboard-panel";
import { UpcomingReleases } from "@/components/intelligence/upcoming-releases";
import { EconomicEvidenceBriefing } from "@/components/research/economic-evidence-briefing";
import { EventsAndThemesSection } from "@/components/research/events-and-themes";
import { loadEconomicEvidence } from "@/lib/research/load-economic-evidence";
import { presentEconomicEvidence } from "@/lib/research/present-economic-evidence";
import {
  NO_REGIONAL_READING,
  STORED_US_READING_HEADING,
  conditionRegion,
  showsStoredUnitedStatesReading,
} from "@/lib/research/present-macro-conditions";

async function DashboardBody({
  searchParams,
}: {
  searchParams: Promise<{ region?: string }>;
}) {
  const params = await searchParams;
  const region = conditionRegion(params.region);
  const loaded = await loadEconomicEvidence();
  const briefing = loaded.status === "ready" ? presentEconomicEvidence(loaded.input) : null;
  const lines = Object.fromEntries((briefing?.seriesLines ?? []).map((line) => [line.sourceId, line.compact]));
  const showUnitedStatesReading = showsStoredUnitedStatesReading(region);
  return (
    <>
      <IntelligenceDashboardSection region={params.region} seriesLines={lines} />
      <UpcomingReleases />
      {showUnitedStatesReading && loaded.status === "unavailable" ? (
        <p className="research-body" data-testid="economic-reading-unavailable">
          {loaded.reason}
        </p>
      ) : null}
      {showUnitedStatesReading && briefing ? (
        <details className="intel-disclosure">
          <summary>Stored family reading</summary>
          <EconomicEvidenceBriefing view={briefing} heading={STORED_US_READING_HEADING} />
        </details>
      ) : null}
      {showUnitedStatesReading ? null : (
        <p className="research-body" data-testid="regional-reading-absent">
          {NO_REGIONAL_READING}
        </p>
      )}
      <details className="intel-disclosure">
        <summary>Events and themes</summary>
        <Suspense fallback={<p className="research-body">Loading events and themes…</p>}>
          <EventsAndThemesSection variant="compact" />
        </Suspense>
      </details>
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
          <Suspense fallback={<p className="research-body">Loading the dashboard…</p>}>
            <DashboardBody searchParams={searchParams} />
          </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
