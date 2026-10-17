import type { ForwardHorizonV1, HorizonEvent } from "@/lib/forward/types";

type Props = {
  bundle: ForwardHorizonV1;
  source: "local" | "fixture";
  compact?: boolean;
};

function materialityLabel(value: HorizonEvent["materiality"]): string {
  switch (value) {
    case "high":
      return "High";
    case "medium":
      return "Medium";
    case "low":
      return "Low";
    default:
      return "Insufficient evidence";
  }
}

export function ForwardHorizonSection({ bundle, source, compact = false }: Props) {
  const events = [...bundle.events]
    .filter((event) => event.scheduled_date !== "unknown")
    .sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date))
    .slice(0, compact ? 3 : 12);

  const banner =
    source === "fixture" || bundle.data_mode === "fixture_demonstration"
      ? "Demonstration forward intelligence (fixture)"
      : bundle.data_mode === "mixed"
        ? "Mixed verified and demonstration forward intelligence"
        : "Forward intelligence preview";

  return (
    <section data-testid="forward-horizon" className="research-banner">
      <p className="research-meta">{banner}</p>
      <h2 className="research-headline">On the horizon</h2>
      {!compact && (
        <p className="research-body">
          Upcoming catalysts linked to vetted ETF exposures. Materiality uses transparent
          rules — not market predictions.
        </p>
      )}
      <ul className="forward-horizon-list">
        {events.map((event) => (
          <li key={event.event_id} className="forward-horizon-item">
            <div className="forward-horizon-item-head">
              <span className="forward-horizon-date">{event.scheduled_date}</span>
              <span className="forward-horizon-materiality">
                {materialityLabel(event.materiality)}
              </span>
            </div>
            <h3 className="forward-horizon-title">{event.title}</h3>
            {!compact && (
              <>
                <p className="research-body">{event.why_it_matters}</p>
                <p className="research-meta">
                  {event.schedule_evidence === "verified_schedule"
                    ? "Schedule verified"
                    : event.schedule_evidence === "synthetic_demonstration"
                      ? "Schedule: demonstration data"
                      : "Schedule unverified"}
                  {" · "}
                  {event.materiality_basis === "calculated"
                    ? "Materiality calculated"
                    : "Materiality not assessed"}
                  {" · Investment interpretation unverified"}
                </p>
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
