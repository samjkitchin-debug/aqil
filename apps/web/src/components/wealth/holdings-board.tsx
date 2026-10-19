import type { PanelHolding, PanelTone } from "@/lib/wealth/panel";

function toneClass(tone: PanelTone | null): string {
  if (tone === "positive") return "aq-result-positive";
  if (tone === "negative") return "aq-result-negative";
  return "";
}

function HoldingDetails({ holding }: { holding: PanelHolding }) {
  return (
    <details className="aq-holding-details">
      <summary>Details</summary>
      <dl>
        <div>
          <dt>Quantity</dt>
          <dd className="aq-num">{holding.quantity}</dd>
        </div>
        {holding.tradingCurrency ? (
          <div>
            <dt>Trading currency</dt>
            <dd>{holding.tradingCurrency}</dd>
          </div>
        ) : null}
        {holding.lots && holding.lots > 1 ? (
          <div>
            <dt>Lots</dt>
            <dd className="aq-num">{holding.lots}</dd>
          </div>
        ) : null}
        <div>
          <dt>Instrument type</dt>
          <dd>{holding.kind}</dd>
        </div>
        {holding.basisLabel ? (
          <div>
            <dt>Value basis</dt>
            <dd>{holding.basisLabel}</dd>
          </div>
        ) : null}
        <div>
          <dt>Price</dt>
          <dd>{holding.priceLabel}</dd>
        </div>
        <div>
          <dt>Classification</dt>
          <dd>Not classified yet</dd>
        </div>
        <div>
          <dt>Account</dt>
          <dd>{holding.accountLabel}</dd>
        </div>
      </dl>
    </details>
  );
}

export function HoldingsBoard({ holdings }: { holdings: PanelHolding[] }) {
  return (
    <section className="aq-holdings-board" id="holdings" aria-labelledby="holdings-title" data-testid="wealth-holdings">
      <div className="aq-section-heading">
        <h2 id="holdings-title">Holdings</h2>
        <p>{holdings.length === 1 ? "1 investment" : `${holdings.length} investments`}</p>
      </div>
      {holdings.length === 0 ? (
        <p className="aq-status aq-status--meta">No positions were returned.</p>
      ) : (
        <div className="aq-holding-table">
          <div className="aq-line aq-line--head" aria-hidden="true">
            <span>Investment</span>
            <span>Value</span>
            <span>Weight</span>
            <span>Open-position result</span>
            <span>Details</span>
          </div>
          <ul className="aq-holding-list">
            {holdings.map((holding) => (
              <li key={holding.key}>
                <article className="aq-line">
                  <div className="aq-line-name">
                    <h3>{holding.name}</h3>
                    <p>
                      {holding.ticker}
                      <span> · {holding.kind}</span>
                    </p>
                  </div>
                  <p className="aq-line-value aq-num">{holding.value ?? "Unavailable"}</p>
                  <p className="aq-line-weight aq-num">
                    {holding.weightLabel ? (
                      <>
                        <span className="aq-only-narrow">Weight </span>
                        {holding.weightLabel}
                      </>
                    ) : (
                      "Weight unavailable"
                    )}
                  </p>
                  <p className={`aq-line-pl aq-num ${toneClass(holding.tone)}`}>
                    {holding.openAmount ? (
                      <>
                        <span className="aq-only-narrow">Open-position </span>
                        <span>{holding.openAmount}</span>
                        {holding.openPercent ? <span className="aq-line-pct">{holding.openPercent} of cost</span> : null}
                      </>
                    ) : (
                      "Open-position result unavailable"
                    )}
                  </p>
                  <HoldingDetails holding={holding} />
                </article>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
