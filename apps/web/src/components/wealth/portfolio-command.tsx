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

  return (
    <section className="aq-command" aria-labelledby="portfolio-value" data-testid="wealth-command">
      {panel.simulation ? <StatusLine tone="simulation">This block is the Saxo simulation account.</StatusLine> : null}
      <p id="portfolio-value" className="aq-kicker">
        Portfolio value
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
      <p className="aq-command-basis">{panel.headline ? panel.headline.basis : "Standard account value is unavailable."}</p>
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
      <p className="aq-fresh">
        <span>Last retrieved {panel.freshness.retrieved}</span>
        <span>{panel.freshness.prices}</span>
        <span>{panel.freshness.connection === "connected" ? "Saxo is connected" : "Saved snapshot"}</span>
        <span>{panel.freshness.environment}</span>
      </p>
      {notice && panel.freshness.connection !== "reconnect" ? <p className="aq-status aq-status--limitation">{notice}</p> : null}
      {notice && panel.freshness.connection === "reconnect" ? <p className="sr-only">{notice}</p> : null}
    </section>
  );
}
