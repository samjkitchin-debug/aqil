import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";

export const dynamic = "force-dynamic";
import { ForwardCalendarSection } from "@/components/forward/forward-calendar-section";
import { ResearchEmptyState } from "@/components/research/research-empty-state";
import { loadForwardHorizonBundle } from "@/lib/forward/load-forward-horizon";

type CalendarSearchParams = Promise<{ horizon?: string }>;

function parseHorizonDays(value: string | undefined): number {
  if (value === "90") return 90;
  return 30;
}

async function CalendarBody({ horizonDays }: { horizonDays: number }) {
  const loaded = await loadForwardHorizonBundle();
  if (loaded.status === "ok") {
    return (
      <ForwardCalendarSection
        bundle={loaded.bundle}
        source={loaded.source}
        horizonDays={horizonDays}
      />
    );
  }
  const reason =
    loaded.status === "unauthorized"
      ? "unauthorized"
      : loaded.status === "invalid"
        ? "invalid"
        : "missing";
  return <ResearchEmptyState reason={reason} />;
}

export default async function CalendarPage({
  searchParams,
}: {
  searchParams: CalendarSearchParams;
}) {
  const params = await searchParams;
  const horizonDays = parseHorizonDays(params.horizon);
  return (
    <AppShell title="Calendar">
      <h1 className="aq-panel-heading mb-[var(--space-4)] font-semibold text-foreground">
        Calendar
      </h1>
      <p className="research-body mb-[var(--space-4)]">
        Forward catalyst view for the vetted ETF research universe. Use{" "}
        <a href="/calendar?horizon=30">30 days</a> or{" "}
        <a href="/calendar?horizon=90">90 days</a>.
      </p>
      <Suspense fallback={<ResearchEmptyState reason="missing" />}>
        <CalendarBody horizonDays={horizonDays} />
      </Suspense>
    </AppShell>
  );
}
