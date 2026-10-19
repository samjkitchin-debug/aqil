import { StatusLine } from "@/components/ui/status-line";
import type { WealthPanel } from "@/lib/wealth/panel";

function toneClass(tone: "positive" | "negative" | "flat" | null): string {
  if (tone === "positive") return "aq-result-positive";
  if (tone === "negative") return "aq-result-negative";
  return "";
}

export function PortfolioCommand({
  panel,
  notice,
}: {
  panel: WealthPanel;
  notice: string | null;
}) {
  const movement = panel.openPosition;
  const month = panel.monthReturn;

  const reconnect = panel.freshness.connection === "reconnect";

  return (
    <section className="aq-command" aria-labelledby="portfolio-value" data-testid="wealth-command">
      {panel.simulation ? <StatusLine tone="simulation">This block is the Saxo simulation account.</StatusLine> : null}
      {reconnect ? <StatusLine tone="limitation">{panel.freshness.connectionLabel}</StatusLine> : null}
      <p id="portfolio-value" className="aq-kicker">
        {panel.headline?.basis ?? "Standard account value"}
      </p>
      {panel.headline ? (
        <div className="aq-command-amount">
          <p className="aq-command-value aq-num" data-testid="wealth-portfolio-value">
            {panel.headline.amount}
          </p>
          <p className="aq-command-ccy">{panel.headline.currency}</p>
        </div>
      ) : (
        <p className="aq-command-value">Unavailable</p>
      )}
      {!panel.headline ? <p className="aq-command-basis">Standard account value is unavailable.</p> : null}
      {movement || month ? (
        <div className="aq-command-results">
          {movement ? (
            <div className="aq-move" data-testid="wealth-open-result">
              <p className="aq-move-label">{movement.label}</p>
              <p className={`aq-move-value aq-num ${toneClass(movement.tone)}`}>{movement.amount}</p>
              {movement.percentOfCost ? (
                <p className={`aq-move-pct aq-num ${toneClass(movement.tone)}`}>{movement.percentOfCost} of cost</p>
              ) : null}
              <p className="aq-move-note">{movement.period}. This is not a return for today or this month.</p>
            </div>
          ) : null}
          {month ? (
            <div className="aq-move">
              <p className="aq-move-label">
                {month.label}
                <span className="aq-move-period"> {month.period}</span>
              </p>
              <p className={`aq-move-value aq-num ${toneClass(month.tone)}`}>{month.text}</p>
              <p className="aq-move-note">Saxo time-weighted return. Separate from open-position gain or loss.</p>
            </div>
          ) : null}
        </div>
      ) : null}
      <p className="aq-fresh">
        <span>Last retrieved {panel.freshness.retrieved}</span>
        <span>{panel.freshness.prices}</span>
        {!reconnect ? <span>{panel.freshness.connectionLabel}</span> : null}
        <span>{panel.freshness.environment}</span>
      </p>
      {notice ? <p className="aq-status aq-status--limitation">{notice}</p> : null}
    </section>
  );
}
