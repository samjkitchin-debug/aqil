import type { WealthPanel } from "@/lib/wealth/panel";

export function AccountDetails({
  panel,
  connectEnabled,
}: {
  panel: WealthPanel;
  connectEnabled: boolean;
}) {
  return (
    <details className="aq-account-details">
      <summary>Account details</summary>
      <dl>
        {panel.standardAmount ? (
          <div>
            <dt>Standard account value</dt>
            <dd className="aq-num">{panel.standardAmount}</dd>
          </div>
        ) : null}
        {panel.extended ? (
          <div>
            <dt>Extended-hours account value</dt>
            <dd>
              <span className="aq-num">{panel.extended.amount}</span>
              <span className="aq-detail-note">
                Saxo extended-hours total, retrieved {panel.extended.retrieved}. Holdings and cash use the standard account value.
              </span>
            </dd>
          </div>
        ) : null}
        {panel.cash ? (
          <div>
            <dt>Cash balance</dt>
            <dd className="aq-num">{panel.cash}</dd>
          </div>
        ) : null}
        {panel.buyingPower ? (
          <div>
            <dt>Buying power</dt>
            <dd>
              <span className="aq-num">{panel.buyingPower}</span>
              <span className="aq-detail-note">This is not cash.</span>
            </dd>
          </div>
        ) : null}
        <div>
          <dt>Environment</dt>
          <dd>{panel.freshness.environment}</dd>
        </div>
        <div>
          <dt>Last retrieved</dt>
          <dd>{panel.freshness.retrieved}</dd>
        </div>
        <div>
          <dt>Prices</dt>
          <dd>{panel.freshness.prices}</dd>
        </div>
      </dl>
      {connectEnabled ? (
        <p className="aq-wealth-actions">
          {panel.freshness.connection === "reconnect" ? (
            <a href="/auth/saxo?environment=live">Reconnect Saxo</a>
          ) : (
            <a href="/auth/saxo/sync">Refresh</a>
          )}
        </p>
      ) : null}
      {panel.limitations.length > 0 ? (
        <div className="aq-source-list">
          <h3>Source information</h3>
          {panel.limitations.map((limitation) => (
            <p key={limitation}>{limitation}</p>
          ))}
        </div>
      ) : null}
    </details>
  );
}
