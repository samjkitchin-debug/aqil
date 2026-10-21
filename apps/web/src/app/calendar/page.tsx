import { Suspense } from "react";

import Link from "next/link";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import {
  CALENDAR_EMPTY_COPY,
  formatOptionalPublishedAt,
  futureSourcePublishedDates,
  presentSourcedUpdate,
} from "@/lib/research/present-sourced-updates";
import { loadSourcedUpdates } from "@/lib/research/load-sourced-updates";
import { loadVerifiedCatalysts } from "@/lib/research/load-verified-catalysts";
import { upcomingCatalysts } from "@/lib/research/present-verified-catalysts";

async function CalendarBody() {
  const sourced = await loadSourcedUpdates();
  const updates = sourced.status === "ok" ? sourced.updates : [];
  const catalysts = futureSourcePublishedDates(updates);
  const verified = upcomingCatalysts(await loadVerifiedCatalysts());

  if (catalysts.length === 0 && verified.listed.length === 0) {
    return (
      <div className="research-banner" data-testid="calendar-empty">
        <p className="research-body">{CALENDAR_EMPTY_COPY}</p>
      </div>
    );
  }

  return (
    <>
      {verified.listed.length > 0 ? (
        <section aria-labelledby="verified-catalysts-heading" data-testid="verified-catalysts">
          <h2 id="verified-catalysts-heading" className="research-section-title">
            Confirmed release times
          </h2>
          <p className="research-body mb-[var(--space-4)]">
            Times stated by the official BLS release calendar for the next 120 days. Not a
            forecast.
          </p>
          <ul className="forward-horizon-list">
            {verified.listed.map((row) => (
              <li key={row.event.eventId} className="forward-horizon-item">
                <div className="forward-horizon-item-head">
                  <span className="forward-horizon-date">{row.scheduleLabel}</span>
                  <span className="forward-horizon-materiality">{row.providerLabel}</span>
                </div>
                <h3 className="forward-horizon-title">
                  <a href={row.event.sourceLocator} rel="noopener noreferrer" target="_blank">
                    {row.event.title}
                  </a>
                </h3>
                <p className="research-meta">
                  Status {row.event.status}. Last verified {row.verifiedLabel}.
                </p>
              </li>
            ))}
          </ul>
          {verified.laterCount > 0 ? (
            <p className="research-meta">
              {verified.laterCount} later confirmed {verified.laterCount === 1 ? "date was" : "dates were"} also retrieved and {verified.laterCount === 1 ? "is" : "are"} not listed here.
            </p>
          ) : null}
        </section>
      ) : null}
      {catalysts.length > 0 ? (
        <ul className="forward-horizon-list" data-testid="calendar-sourced-catalysts">
          {catalysts.map((row) => {
            const presented = presentSourcedUpdate(row);
            return (
              <li key={row.update_id} className="forward-horizon-item">
                <div className="forward-horizon-item-head">
                  <span className="forward-horizon-date">
                    {formatOptionalPublishedAt(row.published_at)}
                  </span>
                  <span className="forward-horizon-materiality">{presented.providerLabel}</span>
                </div>
                <h3 className="forward-horizon-title">
                  <Link href={row.canonical_url} rel="noopener noreferrer" target="_blank">
                    {row.title}
                  </Link>
                </h3>
              </li>
            );
          })}
        </ul>
      ) : null}
    </>
  );
}

export default function CalendarPage() {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/calendar">
          <p className="research-body mb-[var(--space-4)]">
            Upcoming dates stated by retrieved sources. No inferred or modelled schedule is
            shown here.
          </p>
          <Suspense fallback={<p className="research-body">Loading calendar…</p>}>
            <CalendarBody />
          </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
