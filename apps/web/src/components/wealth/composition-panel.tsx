import type { WealthPanel } from "@/lib/wealth/panel";

export function CompositionPanel({ panel }: { panel: WealthPanel }) {
  const composition = panel.composition;
  if (!composition) return null;
  const summary = composition.segments.map((segment) => `${segment.label} ${segment.weightLabel}`).join(", ");

  return (
    <section className="aq-composition" aria-labelledby="portfolio-composition" data-testid="wealth-composition">
      <div className="aq-section-heading">
        <h2 id="portfolio-composition">Portfolio composition</h2>
        <p>{composition.basis}</p>
      </div>
      <div className="aq-stack" role="img" aria-label={`Portfolio composition. ${summary}.`}>
        {composition.segments.map((segment) => (
          <span
            key={segment.key}
            className={`aq-stack-seg aq-seg-${segment.swatch}`}
            style={{ width: `${Math.max(segment.weightPct, 0)}%` }}
          />
        ))}
      </div>
      <ul className="aq-composition-list">
        {composition.segments.map((segment) => (
          <li key={segment.key}>
            <div className="aq-composition-label">
              <span className={`aq-swatch aq-seg-${segment.swatch}`} aria-hidden="true" />
              <span className="aq-composition-name">{segment.label}</span>
              {segment.kind === segment.label ? null : <span className="aq-composition-kind">{segment.kind}</span>}
            </div>
            <div className="aq-track" aria-hidden="true">
              <span
                className={`aq-seg-${segment.swatch}`}
                style={{ width: `${segment.weightPct > 0 ? Math.max(segment.weightPct, 1.5) : 0}%` }}
              />
            </div>
            <p className="aq-composition-figures aq-num">
              <span>{segment.weightLabel}</span>
              <span>{segment.valueLabel}</span>
            </p>
          </li>
        ))}
      </ul>
      {composition.etfNote ? (
        <p className="aq-composition-note">Each percentage is that holding&apos;s share of this account. An ETF remains one holding.</p>
      ) : null}
    </section>
  );
}
