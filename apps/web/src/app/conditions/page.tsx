import { Suspense } from "react";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import { EventsAndThemesSection } from "@/components/research/events-and-themes";
import { MacroConditionsSection } from "@/components/research/macro-conditions-panel";

export default function ConditionsPage() {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/conditions">
          <section aria-labelledby="conditions-heading">
            <h2 id="conditions-heading" className="research-section-title">
              Conditions
            </h2>
            <Suspense fallback={<p className="research-body">Loading conditions…</p>}>
              <MacroConditionsSection variant="dashboard" />
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
