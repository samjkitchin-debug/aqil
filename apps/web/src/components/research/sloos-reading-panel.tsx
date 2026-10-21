import {
  directionPhrase,
  quarterStartingLabel,
  sloosLimitationCopy,
  sloosMonitorCopy,
  whyItMatters,
  type SloosReadingView,
} from "@/lib/research/present-sloos-reading";

type Props = {
  reading: SloosReadingView;
};

export function SloosReadingPanel({ reading }: Props) {
  return (
    <section aria-labelledby="credit-standards-heading" data-testid="credit-standards">
      <h2 id="credit-standards-heading" className="research-section-title">
        Business credit standards
      </h2>
      <p className="research-body">{reading.narrative}</p>
      <p className="research-meta">
        Net tightening share {reading.sharePercent} percent for the quarter starting{" "}
        {quarterStartingLabel(reading.observationPeriod)}. Direction:{" "}
        {directionPhrase(reading.directionLabel)}.
      </p>
      <h3 className="research-section-title">Why it matters</h3>
      <p className="research-body">{whyItMatters(reading.directionLabel, reading.interpretation)}</p>
      {reading.previousPeriod && reading.previousSharePercent ? (
        <p className="research-meta">
          Previous stored quarter, starting {quarterStartingLabel(reading.previousPeriod)}:{" "}
          {reading.previousSharePercent} percent. That is another stored reading, not a forecast.
        </p>
      ) : null}
      <h3 className="research-section-title">What remains uncertain</h3>
      <p className="research-body">{sloosLimitationCopy(reading.limitations)}</p>
      <h3 className="research-section-title">What to monitor</h3>
      <p className="research-body">{sloosMonitorCopy()}</p>
      <dl className="research-meta">
        <div>
          <dt>Source id</dt>
          <dd>{reading.sourceId}</dd>
        </div>
        <div>
          <dt>Dataset</dt>
          <dd>{reading.datasetId}</dd>
        </div>
        <div>
          <dt>Method</dt>
          <dd>
            {reading.methodId} {reading.methodVersion}
          </dd>
        </div>
        <div>
          <dt>Analysis mode</dt>
          <dd>{reading.analysisMode}</dd>
        </div>
        <div>
          <dt>Observation</dt>
          <dd>{reading.observationId}</dd>
        </div>
        <div>
          <dt>Retrieved</dt>
          <dd>{reading.retrievedAt}</dd>
        </div>
        <div>
          <dt>Run</dt>
          <dd>{reading.runId}</dd>
        </div>
        <div>
          <dt>Payload hash</dt>
          <dd>{reading.payloadHash.slice(0, 16)}…</dd>
        </div>
      </dl>
      <p className="research-meta">
        Not an investment conclusion. No price target, expected return, or fund recommendation is
        made. Publication remains closed.
      </p>
    </section>
  );
}
