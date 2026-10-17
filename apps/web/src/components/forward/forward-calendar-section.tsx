import type { ForwardHorizonV1, HorizonEvent } from "@/lib/forward/types";

type Props = {
  bundle: ForwardHorizonV1;
  source: "local" | "fixture";
  horizonDays: number;
};

function withinHorizon(event: HorizonEvent, horizonDays: number, today: string): boolean {
  if (event.scheduled_date === "unknown") {
    return false;
  }
  const start = new Date(`${today}T00:00:00Z`);
  const end = new Date(start);
  end.setUTCDate(end.getUTCDate() + horizonDays);
  const when = new Date(`${event.scheduled_date}T00:00:00Z`);
  return when >= start && when <= end;
}

export function ForwardCalendarSection({ bundle, source, horizonDays }: Props) {
  const today = bundle.generated_at.slice(0, 10);
  const events = bundle.events
    .filter((event) => withinHorizon(event, horizonDays, today))
    .sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date));

  const banner =
    source === "fixture" || bundle.data_mode === "fixture_demonstration"
      ? "Demonstration calendar (fixture)"
      : bundle.data_mode === "mixed"
        ? "Mixed verified and demonstration events"
        : "Source-backed forward calendar";

  return (
    <section data-testid="forward-calendar" className="research-banner">
      <p className="research-meta">{banner}</p>
      <h2 className="research-headline">Next {horizonDays} days</h2>
      <p className="research-body">
        Showing {events.length} scheduled catalyst{events.length === 1 ? "" : "s"} with a known
        date in this window.
      </p>
      <ul className="forward-horizon-list">
        {events.map((event) => (
          <li key={event.event_id} className="forward-horizon-item">
            <div className="forward-horizon-item-head">
              <span className="forward-horizon-date">{event.scheduled_date}</span>
              <span className="research-meta">
                {event.is_fixture ? "Demonstration" : "Verified source"}
              </span>
            </div>
            <h3 className="forward-horizon-title">{event.title}</h3>
            <p className="research-body">{event.why_it_matters}</p>
            <p className="research-meta">
              {event.date_precision === "tentative"
                ? "Official schedule (tentative)"
                : event.schedule_evidence === "verified_schedule"
                  ? "Official schedule (confirmed)"
                  : "Schedule not verified"}
            </p>
          </li>
        ))}
      </ul>
      {events.length === 0 && (
        <p className="research-body">No dated events fall in this horizon window.</p>
      )}
    </section>
  );
}
