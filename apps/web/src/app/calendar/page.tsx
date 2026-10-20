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

async function CalendarBody() {
  const sourced = await loadSourcedUpdates();
  const updates = sourced.status === "ok" ? sourced.updates : [];
  const catalysts = futureSourcePublishedDates(updates);

  if (catalysts.length === 0) {
    return (
      <div className="research-banner" data-testid="calendar-empty">
        <p className="research-body">{CALENDAR_EMPTY_COPY}</p>
      </div>
    );
  }

  return (
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
