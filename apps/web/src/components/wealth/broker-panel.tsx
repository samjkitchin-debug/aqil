import { AccountDetails } from "@/components/wealth/account-details";
import { CompositionPanel } from "@/components/wealth/composition-panel";
import { HoldingsBoard } from "@/components/wealth/holdings-board";
import { PortfolioCommand } from "@/components/wealth/portfolio-command";
import { ValueChart } from "@/components/wealth/value-chart";
import { WealthMetrics } from "@/components/wealth/wealth-metrics";
import type { WealthPanel } from "@/lib/wealth/panel";

export function BrokerPanel({
  panel,
  notice,
  connectEnabled,
  heading,
}: {
  panel: WealthPanel;
  notice: string | null;
  connectEnabled: boolean;
  heading: "h1" | "h2";
}) {
  const Title = heading;
  const action =
    panel.freshness.connection === "reconnect"
      ? { href: "/auth/saxo?environment=live", label: "Reconnect Saxo", attention: true }
      : { href: "/auth/saxo/sync", label: "Refresh", attention: false };

  return (
    <div className="aq-wealth" data-testid="wealth-panel">
      <div className="aq-wealth-toolbar">
        {heading === "h1" || panel.headline ? <Title className="aq-wealth-title">My wealth</Title> : null}
        <div className="aq-wealth-toolbar-actions">
          <a className="aq-quiet-link" href="#holdings">
            View holdings
          </a>
          <a className="aq-quiet-link" href="/my-wealth/deploy">
            Deploy capital
          </a>
          {connectEnabled ? (
            <a className={action.attention ? "aq-pill aq-pill--attention" : "aq-pill"} href={action.href}>
              {action.label}
            </a>
          ) : null}
        </div>
      </div>
      <div className="aq-cockpit">
        <div className="aq-cockpit-primary">
          <PortfolioCommand panel={panel} notice={notice} />
          <WealthMetrics panel={panel} />
        </div>
        {panel.chart ? (
          <ValueChart
            points={panel.chart.points}
            from={panel.chart.from}
            to={panel.chart.to}
            currency={panel.chart.currency}
          />
        ) : null}
      </div>
      <CompositionPanel panel={panel} />
      <HoldingsBoard holdings={panel.holdings} />
      <AccountDetails panel={panel} connectEnabled={connectEnabled} />
    </div>
  );
}
