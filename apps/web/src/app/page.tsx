import { Suspense } from "react";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import { MacroConditionsSection } from "@/components/research/macro-conditions-panel";
import { ResearchInsightView } from "@/components/research/research-insight-view";
import { EventsAndThemesSection } from "@/components/research/events-and-themes";
import { SourcedUpdatesPanel } from "@/components/research/sourced-updates-panel";
import { loadFounderResearchInsight } from "@/lib/research/load-founder-insight";
import { loadSourcedUpdates } from "@/lib/research/load-sourced-updates";
import { loadVerifiedCatalysts } from "@/lib/research/load-verified-catalysts";
import { upcomingCatalysts } from "@/lib/research/present-verified-catalysts";

async function NextConfirmedRelease() {
  const loaded = await loadVerifiedCatalysts();
  if (loaded.status === "unavailable") {
    return <p className="research-body">{loaded.reason}</p>;
  }
  const next = upcomingCatalysts(loaded.events).listed[0];
  if (!next) return null;
  return (
    <section aria-labelledby="next-release-heading" className="mt-[var(--space-6)]">
      <h2 id="next-release-heading" className="research-section-title">
        Next confirmed release
      </h2>
      <p className="research-body">{next.event.title}</p>
      <p className="research-meta">
        {next.scheduleLabel}. {next.providerLabel}. Last verified {next.verifiedLabel}.
      </p>
      <p className="research-meta">Stated by the official calendar. Not a forecast.</p>
    </section>
  );
}

async function TodayBriefing() {
  const sourced = await loadSourcedUpdates();
  if (sourced.status === "unavailable") {
    return <p className="research-body">{sourced.reason}</p>;
  }
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
          <Suspense fallback={<p className="research-body">Loading material developments…</p>}>
            <EventsAndThemesSection variant="today" />
          </Suspense>
          <section aria-labelledby="sourced-briefing-heading">
            <h2 id="sourced-briefing-heading" className="research-section-title">
              Sourced publications
            </h2>
            <Suspense fallback={<p className="research-body">Loading sourced publications…</p>}>
              <TodayBriefing />
            </Suspense>
          </section>
          <section aria-labelledby="macro-pulse-heading">
            <h2 id="macro-pulse-heading" className="research-section-title">
              Macro pulse
            </h2>
            <Suspense fallback={<p className="research-body">Loading macro pulse…</p>}>
              <MacroConditionsSection variant="compact" />
            </Suspense>
          </section>
          <Suspense fallback={null}>
            <NextConfirmedRelease />
          </Suspense>
          <Suspense fallback={null}>
            <SahmPreviewBlock />
          </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
