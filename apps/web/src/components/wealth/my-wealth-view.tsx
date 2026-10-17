import { ContributionScenarioPanel } from "@/components/wealth/contribution-scenario-panel";
import {
  computePortfolioAnalytics,
} from "@/lib/wealth/analytics";
import { formatMinor } from "@/lib/wealth/minor-units";
import { fromWire, type WealthSnapshotWire } from "@/lib/wealth/serialize";

type Props = {
  snapshot: WealthSnapshotWire;
};

function bpsToPercent(bps: number): string {
  return `${(bps / 100).toFixed(1)}%`;
}

export function MyWealthView({ snapshot }: Props) {
  const model = fromWire(snapshot);
  const analytics = computePortfolioAnalytics(
    model.positions,
    model.targets,
    model.profile.emergencyReserveMinor,
  );

  const banner =
    snapshot.source === "fixture"
      ? "Demonstration portfolio (synthetic fixture)"
      : "Private portfolio — not publicly verified";

  return (
    <article className="wealth-page" data-testid="my-wealth">
      <header className="wealth-banner">
        <p className="wealth-meta">{banner}</p>
        <h2 className="wealth-headline">How is my long-term plan progressing?</h2>
        <p className="wealth-body">
          Investable total{" "}
          <strong>{formatMinor(analytics.investableTotalMinor, model.profile.baseCurrency)}</strong>
          . Emergency reserve{" "}
          <strong>
            {formatMinor(analytics.emergencyReserveMinor, model.profile.baseCurrency)}
          </strong>{" "}
          (excluded from allocation maths).
        </p>
        {snapshot.dataFreshness.oldestValuationDate ? (
          <p className="wealth-meta" data-testid="valuation-freshness">
            Valuations as of {snapshot.dataFreshness.oldestValuationDate}
            {snapshot.dataFreshness.missingValuationCount > 0
              ? ` · ${snapshot.dataFreshness.missingValuationCount} position(s) missing dates`
              : ""}
          </p>
        ) : (
          <p className="wealth-warning">Valuation dates missing — weights may be incomplete.</p>
        )}
      </header>

      <section className="wealth-panel">
        <h3 className="wealth-section-title">Strategic target vs actual</h3>
        {!analytics.targetsComplete ? (
          <p className="wealth-warning">
            Strategic targets do not sum to 100% or are missing. Drift diagnostics are limited.
          </p>
        ) : null}
        <table className="wealth-table">
          <thead>
            <tr>
              <th scope="col">Asset class</th>
              <th scope="col">Actual</th>
              <th scope="col">Target</th>
              <th scope="col">Drift</th>
            </tr>
          </thead>
          <tbody>
            {analytics.classWeights.map((row) => (
              <tr key={row.assetClass}>
                <td>{row.assetClass.replaceAll("_", " ")}</td>
                <td>{bpsToPercent(row.actualBps)}</td>
                <td>{row.targetBps === null ? "—" : bpsToPercent(row.targetBps)}</td>
                <td>
                  {row.driftBps === null
                    ? "—"
                    : `${row.driftBps > 0 ? "+" : ""}${bpsToPercent(row.driftBps)}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="wealth-panel">
        <h3 className="wealth-section-title">Holdings</h3>
        <ul className="wealth-holdings-list">
          {model.positions.map((position) => (
            <li key={position.id}>
              <div>
                <strong>{position.name}</strong>
                {position.isin ? (
                  <span className="wealth-meta"> · ISIN {position.isin}</span>
                ) : null}
              </div>
              <div className="wealth-meta">
                {position.assetClass.replaceAll("_", " ")}
                {position.thematicLabel ? ` · ${position.thematicLabel}` : ""}
              </div>
              <div>{formatMinor(position.marketValueMinor, position.currency)}</div>
            </li>
          ))}
        </ul>
      </section>

      {analytics.largestFund ? (
        <section className="wealth-panel">
          <h3 className="wealth-section-title">Concentration</h3>
          <p className="wealth-body">
            Largest fund: {analytics.largestFund.name} at{" "}
            {bpsToPercent(analytics.largestFund.concentrationBps)} of investable assets.
          </p>
          {analytics.thematicExposure.length > 0 ? (
            <ul className="wealth-allocation-list">
              {analytics.thematicExposure.map((row) => (
                <li key={row.label}>
                  <span>{row.label}</span>
                  <span>{bpsToPercent(row.bps)}</span>
                </li>
              ))}
            </ul>
          ) : null}
          <p className="wealth-meta" data-testid="overlap-unavailable">
            Issuer-level ETF overlap is unavailable without licensed holdings data. Aqil does not
            infer constituent exposure from an ISIN alone.
          </p>
        </section>
      ) : null}

      <section className="wealth-panel">
        <h3 className="wealth-section-title">Planned contributions</h3>
        {model.contributionPlan ? (
          <p className="wealth-body">
            {model.contributionPlan.cadence} contribution of{" "}
            {formatMinor(model.contributionPlan.amountMinor, model.contributionPlan.currency)}
            {model.contributionPlan.dayOfMonth
              ? ` on day ${model.contributionPlan.dayOfMonth}`
              : ""}
            .
          </p>
        ) : (
          <p className="wealth-meta">No contribution plan recorded.</p>
        )}
        <h4 className="wealth-subtitle">History</h4>
        {model.contributionHistory.length === 0 ? (
          <p className="wealth-meta">No contributions recorded yet.</p>
        ) : (
          <ul className="wealth-allocation-list">
            {model.contributionHistory.map((event) => (
              <li key={event.id}>
                <span>{new Date(event.occurredAt).toLocaleDateString("en-GB")}</span>
                <span>{formatMinor(event.amountMinor, event.currency)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <ContributionScenarioPanel snapshot={snapshot} />

      <footer className="wealth-footer">
        <p className="wealth-meta">
          Research outputs do not change strategic targets or generate trades. Past composition is
          not a performance guarantee.
        </p>
      </footer>
    </article>
  );
}
