import Link from "next/link";

import { loadVerifiedCatalysts } from "@/lib/research/load-verified-catalysts";
import { upcomingCatalysts } from "@/lib/research/present-verified-catalysts";

const PREVIEW_LIMIT = 4;

export async function UpcomingReleases() {
  const loaded = await loadVerifiedCatalysts();
  if (loaded.status === "unavailable") {
    return (
      <section className="intel-releases" aria-labelledby="upcoming-releases-heading">
        <h2 id="upcoming-releases-heading" className="intel-section-title">
          Upcoming releases
        </h2>
        <p className="research-body">{loaded.reason}</p>
      </section>
    );
  }
  const verified = upcomingCatalysts(loaded.events);
  const preview = verified.listed.slice(0, PREVIEW_LIMIT);
  const remaining = verified.listed.length - preview.length;
  return (
    <section className="intel-releases" aria-labelledby="upcoming-releases-heading" data-testid="upcoming-releases">
      <div className="intel-releases-head">
        <h2 id="upcoming-releases-heading" className="intel-section-title">
          Upcoming releases
        </h2>
        <Link href="/calendar" prefetch={false}>
          Full calendar
        </Link>
      </div>
      <p className="research-meta">Confirmed times from the stored calendar. No forecast is shown.</p>
      {preview.length === 0 ? (
        <p className="research-body">No confirmed release is stored in the next 120 days.</p>
      ) : (
        <ul className="intel-release-list">
          {preview.map((row) => (
            <li key={row.event.eventId}>
              <span className="intel-release-when">{row.scheduleLabel}</span>
              <a href={row.event.sourceLocator} rel="noopener noreferrer" target="_blank">
                {row.event.title}
              </a>
              <span className="intel-release-who">{row.providerLabel}</span>
            </li>
          ))}
        </ul>
      )}
      {remaining > 0 ? (
        <p className="research-meta">
          {remaining} more confirmed {remaining === 1 ? "release is" : "releases are"} on the full calendar.
        </p>
      ) : null}
    </section>
  );
}
