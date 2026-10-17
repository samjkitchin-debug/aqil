import type { ForwardHorizonV1 } from "@/lib/forward/types";

type Props = {
  bundle: ForwardHorizonV1;
};

function pickScenario(bundle: ForwardHorizonV1) {
  const scenarios = bundle.scenarios ?? [];
  const verified = scenarios.find(
    (row) =>
      row.evidence_class === "research_assessment" && row.record_source === "database",
  );
  if (verified) {
    return verified;
  }
  return scenarios[0];
}

export function ForwardResearchDetail({ bundle }: Props) {
  const scenario = pickScenario(bundle);
  const outcome =
    bundle.outcomes?.find((row) => row.scenario_id === scenario?.scenario_id) ??
    bundle.outcomes?.[0];
  const event = bundle.events.find((row) => row.event_id === scenario?.event_id);

  if (!scenario || !event) {
    return (
      <p className="research-body">No frozen forward scenario is available in this bundle.</p>
    );
  }

  const isDemo = scenario.evidence_class === "synthetic_demonstration";

  return (
    <section data-testid="forward-research-detail" className="research-banner">
      <p className="research-meta">
        {isDemo
          ? "Synthetic demonstration scenario"
          : "Source-backed pre-event assessment (frozen before the event)"}
        {scenario.record_source === "database" ? " · Loaded from the frozen record" : ""}
      </p>
      <h2 className="research-headline">{scenario.headline}</h2>
      <p className="research-body">Catalyst: {event.title}</p>
      {scenario.expected_information && (
        <p className="research-body">
          <strong>Expected information:</strong> {scenario.expected_information}
        </p>
      )}
      {scenario.known_facts && scenario.known_facts.length > 0 && (
        <ul className="forward-horizon-list">
          {scenario.known_facts.map((fact) => (
            <li key={fact} className="research-meta">{fact}</li>
          ))}
        </ul>
      )}
      {scenario.inconclusive && (
        <p className="research-body">
          <strong>Uncertainty:</strong> {scenario.inconclusive}
        </p>
      )}
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
      {scenario.no_action_conclusion && (
        <p className="research-body">
          <strong>No-action conclusion:</strong> {scenario.no_action_conclusion}
        </p>
      )}
      {scenario.what_would_change_assessment && scenario.what_would_change_assessment.length > 0 && (
        <>
          <h3 className="research-section-title">What would change this assessment</h3>
          <ul className="forward-horizon-list">
            {scenario.what_would_change_assessment.map((item) => (
              <li key={item} className="research-meta">{item}</li>
            ))}
          </ul>
        </>
      )}
      {outcome && isDemo && (
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
