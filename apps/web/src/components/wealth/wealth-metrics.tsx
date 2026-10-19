import type { WealthPanel } from "@/lib/wealth/panel";

export function WealthMetrics({ panel }: { panel: WealthPanel }) {
  const largest = panel.largest;
  return (
    <section className="aq-meters" aria-label="Account figures">
      <article className="aq-meter">
        <h2 className="aq-kicker">Cash balance</h2>
        <p className="aq-meter-value aq-num">{panel.cash ?? "Unavailable"}</p>
      </article>
      <article className="aq-meter">
        <h2 className="aq-kicker">Investments held</h2>
        <p className="aq-meter-value aq-num">{panel.investmentCount}</p>
      </article>
      <article className="aq-meter">
        <h2 className="aq-kicker">Largest holding</h2>
        {largest ? (
          <>
            <p className="aq-meter-value">{largest.ticker}</p>
            <p className="aq-meter-detail">
              {largest.kind} · {largest.weightLabel}
            </p>
          </>
        ) : (
          <p className="aq-meter-value">Unavailable</p>
        )}
      </article>
      <article className="aq-meter">
        <h2 className="aq-kicker">Connection</h2>
        <p className="aq-meter-value aq-meter-value--text">{panel.freshness.connectionLabel}</p>
        <p className="aq-meter-detail">{panel.freshness.environment}</p>
      </article>
    </section>
  );
}
