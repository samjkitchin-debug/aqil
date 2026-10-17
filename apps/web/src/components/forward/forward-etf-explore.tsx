import type { ForwardHorizonV1 } from "@/lib/forward/types";

type Props = {
  bundle: ForwardHorizonV1;
};

export function ForwardEtfExplore({ bundle }: Props) {
  const etf = bundle.etfs[0];
  if (!etf) {
    return (
      <p className="research-body">No vetted ETF records are available in this bundle.</p>
    );
  }

  const relatedEvents = bundle.events.filter((event) =>
    event.etf_ids.includes(etf.etf_id),
  );

  return (
    <div data-testid="forward-etf-explore" className="forward-etf-card">
      <h2 className="research-headline">{etf.legal_name}</h2>
      <p className="research-meta">
        {etf.ticker} · {etf.exchange}
        {etf.isin ? ` · ISIN ${etf.isin}` : ""}
      </p>
      <p className="research-body">
        Holdings snapshot as of {etf.holdings_as_of}. Completeness: {etf.completeness}.
      </p>
      {bundle.data_mode !== "verified_source" && (
        <p className="research-meta">
          Synthetic demonstration weights and catalysts — not provider or consensus data.
        </p>
      )}
      <h3 className="research-section-title">Largest supported exposures</h3>
      <ul className="forward-horizon-list">
        {etf.top_holdings.map((line) => (
          <li key={line.name} className="forward-horizon-item">
            <span className="forward-horizon-title">{line.name}</span>
            <span className="research-meta">{line.weight_percentage}%</span>
          </li>
        ))}
      </ul>
      <h3 className="research-section-title">Upcoming relevant events</h3>
      {relatedEvents.length === 0 ? (
        <p className="research-body">No linked events in this bundle.</p>
      ) : (
        <ul className="forward-horizon-list">
          {relatedEvents.map((event) => (
            <li key={event.event_id} className="forward-horizon-item">
              <span className="forward-horizon-date">{event.scheduled_date}</span>
              <p className="forward-horizon-title">{event.title}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
