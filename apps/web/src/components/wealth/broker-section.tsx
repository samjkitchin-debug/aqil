import { formatAccumulatedReturn } from "@/lib/saxo/performance";
import {
  formatQuantity,
  formatReportedAmount,
  formatRetrievedAt,
  type BrokerHoldingView,
  type BrokerPortfolioView,
} from "@/lib/saxo/portfolio";
import { StatusLine } from "@/components/ui/status-line";

const SAXO_ERRORS: Record<string, string> = {
  saxo_unavailable: "Saxo is not available from this address.",
  saxo_denied: "Saxo authorisation was cancelled.",
  saxo_state: "That Saxo return did not match this sign-in. Connect again.",
  saxo_user: "This Saxo connection belongs to a different Aqil sign-in.",
  saxo_exchange: "Saxo did not complete the connection.",
  no_session: "Connect Saxo before refreshing.",
  refresh_failed: "The Saxo connection needs to be renewed.",
  source_error: "Saxo did not return a complete portfolio. The last good snapshot is unchanged.",
  incomplete_kept: "This refresh did not replace the stored snapshot.",
};

export function saxoErrorMessage(error: string | null): string | null {
  if (!error) return null;
  return SAXO_ERRORS[error] ?? null;
}

function rankedHoldings(holdings: BrokerHoldingView[]): BrokerHoldingView[] {
  return [...holdings].sort((left, right) => valueOf(right) - valueOf(left));
}

function valueOf(holding: BrokerHoldingView): number {
  if (holding.marketValue === null) return Number.NEGATIVE_INFINITY;
  const amount = Number(holding.marketValue);
  return Number.isFinite(amount) ? amount : Number.NEGATIVE_INFINITY;
}

function resultClass(value: string | null): string {
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount === 0) return "";
  return amount > 0 ? "aq-result-positive" : "aq-result-negative";
}

function ValueChart({ points }: { points: { date: string; value: string }[] }) {
  const values = points.map((point) => Number(point.value)).filter((value) => Number.isFinite(value));
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 320;
  const height = 96;
  const coords = values.map((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - ((value - min) / span) * (height - 8) - 4;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  return (
    <svg className="aq-value-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Account value, including contributions">
      <polyline fill="none" stroke="currentColor" strokeWidth="2" points={coords.join(" ")} />
    </svg>
  );
}

export function BrokerSection({
  broker,
  error,
  connectEnabled,
  heading,
}: {
  broker: BrokerPortfolioView | null;
  error: string | null;
  connectEnabled: boolean;
  heading: "h1" | "h2";
}) {
  const message = saxoErrorMessage(error);
  const Title = heading;
  const account = broker?.accounts[0];
  const primaryValue = account?.extendedReportedValue ?? account?.brokerReportedValue ?? null;
  const primaryCurrency = account?.currency ?? null;
  const showStandard =
    account?.extendedReportedValue != null &&
    account.brokerReportedValue != null &&
    account.extendedReportedValue !== account.brokerReportedValue;
  const holdings = broker ? rankedHoldings(broker.holdings) : [];
  const sharedCurrency = holdings.every((holding) => holding.currency && holding.currency === holdings[0]?.currency);
  const weightTotal = sharedCurrency
    ? holdings.reduce((sum, holding) => sum + (Number.isFinite(Number(holding.marketValue)) ? Number(holding.marketValue) : 0), 0)
    : 0;
  const largest = holdings.find((holding) => holding.marketValue !== null);
  const performance = broker?.performance?.status === "ok" ? broker.performance : null;
  const latestReturn = performance?.timeWeightedAccumulated.at(-1) ?? null;
  const returnText = performance ? formatAccumulatedReturn(latestReturn?.value ?? null) : null;
  const needsReconnect = error === "refresh_failed" || error === "no_session" || error === "saxo_exchange";

  return (
    <section className="aq-wealth-summary">
      {broker || heading === "h1" ? <Title className="aq-page-title">My wealth</Title> : null}
      {message ? <p>{message}</p> : null}
      {broker && account ? (
        <>
          <p className="aq-figure aq-num">{formatReportedAmount(primaryValue, primaryCurrency)}</p>
          <p className="aq-status aq-status--meta">
            {showStandard ? "Account value, including extended hours." : "Account value."}{" "}
            {broker.environment === "live" ? "Saxo live" : "Saxo simulation"}. As of {formatRetrievedAt(broker.retrievedAt)}.
          </p>
          {broker.environment === "simulation" ? (
            <StatusLine tone="simulation">This block is the Saxo simulation account.</StatusLine>
          ) : null}
          {showStandard ? (
            <p>
              Standard account value {formatReportedAmount(account.brokerReportedValue, account.currency)}. Cash and holdings
              below use this valuation.
            </p>
          ) : null}
          {performance && returnText ? (
            <p>
              Time-weighted return, Saxo month{" "}
              <span className={`aq-num ${resultClass(latestReturn?.value ?? null)}`}>{returnText}</span>
            </p>
          ) : (
            <p className="aq-status aq-status--meta">Historical account value and time-weighted return are not available yet.</p>
          )}
          {performance && performance.accountValue.length > 1 ? (
            <figure className="aq-value-figure">
              <ValueChart points={performance.accountValue} />
              <figcaption className="aq-status aq-status--meta">
                Account value, including contributions. {performance.accountValue[0]?.date} to{" "}
                {performance.accountValue.at(-1)?.date}.
                {performance.currency ? ` ${performance.currency}.` : ""} This series is separate from the account value above.
              </figcaption>
            </figure>
          ) : null}
          <p>
            Cash {formatReportedAmount(account.cashBalance, account.currency)}
            {largest ? `. Largest holding ${largest.name}.` : "."}
          </p>
          {account.buyingPower && account.buyingPower !== account.cashBalance ? (
            <p className="aq-status aq-status--meta">
              Buying power {formatReportedAmount(account.buyingPower, account.currency)}. This is not cash.
            </p>
          ) : null}
          {connectEnabled ? (
            <p className="aq-wealth-actions">
              <a href="/auth/saxo/sync">Refresh</a>
              {needsReconnect ? (
                <>
                  {" "}
                  <a href="/auth/saxo?environment=live">Connect again</a>
                </>
              ) : null}
            </p>
          ) : null}
          {holdings.length === 0 ? (
            <p className="aq-status aq-status--meta">No positions were returned.</p>
          ) : (
            <div className="aq-table-scroll">
              <table className="aq-holdings">
                <caption className="sr-only">Holdings ranked by value</caption>
                <thead>
                  <tr>
                    <th>Instrument</th>
                    <th>Quantity</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((holding, index) => {
                    const weight =
                      weightTotal > 0 && holding.marketValue ? Math.max(0, (Number(holding.marketValue) / weightTotal) * 100) : null;
                    return (
                      <tr key={`${holding.uic ?? holding.symbol ?? holding.name}-${index}`}>
                        <td>
                          <span className="aq-holding-name">{holding.name}</span>
                          {weight !== null ? (
                            <span className="aq-weight" aria-hidden="true">
                              <span style={{ width: `${weight}%` }} />
                            </span>
                          ) : null}
                          <span className="aq-holding-meta">
                            {holding.symbol ?? "No symbol"}. {holding.assetType ?? "Unknown type"}. Unclassified.
                            {holding.tradingCurrency && holding.tradingCurrency !== holding.currency
                              ? ` Traded in ${holding.tradingCurrency}.`
                              : ""}
                            {holding.lotCount && holding.lotCount > 1 ? ` ${holding.lotCount} lots.` : ""}
                          </span>
                        </td>
                        <td className="aq-num">{formatQuantity(holding.quantity)}</td>
                        <td className="aq-num">
                          {holding.marketValue ? formatReportedAmount(holding.marketValue, holding.currency) : "Unavailable"}
                          {holding.profitLoss ? (
                            <span className={`aq-holding-meta ${resultClass(holding.profitLoss)}`}>
                              Price result {formatReportedAmount(holding.profitLoss, holding.currency)}
                            </span>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {broker.limitations.length > 0 ? (
            <details className="aq-source-details">
              <summary>Source details</summary>
              {broker.limitations.map((limitation) => (
                <p key={limitation}>{limitation}</p>
              ))}
            </details>
          ) : null}
        </>
      ) : connectEnabled ? (
        <p>
          <a className="aq-button" href="/auth/saxo?environment=live">
            Connect Saxo
          </a>
        </p>
      ) : (
        <p className="aq-status aq-status--meta">A Saxo connection is not available on this site yet.</p>
      )}
    </section>
  );
}
