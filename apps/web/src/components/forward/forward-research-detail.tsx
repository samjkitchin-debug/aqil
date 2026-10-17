import type { ForwardHorizonV1 } from "@/lib/forward/types";

type Props = {
  bundle: ForwardHorizonV1;
};

export function ForwardResearchDetail({ bundle }: Props) {
  const scenario = bundle.scenarios?.[0];
  const outcome = bundle.outcomes?.[0];
  const event = bundle.events.find((row) => row.event_id === scenario?.event_id);

  if (!scenario || !event) {
    return (
      <p className="research-body">No frozen forward scenario is available in this bundle.</p>
    );
  }

  return (
    <section data-testid="forward-research-detail" className="research-banner">
      <p className="research-meta">
        Synthetic demonstration scenario
        {scenario.record_source === "database" ? " · Loaded from the frozen record" : ""}
      </p>
      <h2 className="research-headline">{scenario.headline}</h2>
      <p className="research-body">Catalyst: {event.title}</p>
      {scenario.upside_case && (
        <p className="research-body">
          <strong>Upside case:</strong> {scenario.upside_case}
        </p>
      )}
      {scenario.downside_case && (
        <p className="research-body">
          <strong>Downside case:</strong> {scenario.downside_case}
        </p>
      )}
      {scenario.evidence_gaps && scenario.evidence_gaps.length > 0 && (
        <ul className="forward-horizon-list">
          {scenario.evidence_gaps.map((gap) => (
            <li key={gap} className="research-meta">{gap}</li>
          ))}
        </ul>
      )}
      {outcome && (
        <div className="forward-etf-card" data-testid="forward-outcome-block">
          <p className="research-meta">
            Synthetic demonstration outcome · References the frozen scenario
          </p>
          <h3 className="research-section-title">What happened</h3>
          <p className="research-body">{outcome.headline}</p>
          {outcome.surprise_assessment && (
            <p className="research-meta">Surprise: {outcome.surprise_assessment}</p>
          )}
        </div>
      )}
    </section>
  );
}
