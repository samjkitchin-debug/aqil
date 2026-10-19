import { exampleDeployment, unconfiguredDeployment } from "@/lib/capital/example";
import { deployCapital, type ClassExposure, type DeployCapitalResult } from "@/lib/capital/deploy";
import { formatMinor } from "@/lib/wealth/money";

const CLASS_LABELS: Record<ClassExposure["assetClass"], string> = {
  global_equity: "Global equity",
  thematic_technology: "Thematic technology",
  investment_grade_bonds: "Investment-grade bonds",
  cash_investable: "Investable cash",
};

function weight(bps: number): string {
  const whole = Math.trunc(bps / 100);
  const fraction = Math.abs(bps % 100).toString().padStart(2, "0");
  return `${whole}.${fraction}%`;
}

function ResultTable({ result }: { result: DeployCapitalResult }) {
  return (
    <div className="grid gap-[var(--space-4)]">
      {result.missing.length > 0 ? (
        <p>
          Not configured: {result.missing.join(", ")}.
        </p>
      ) : (
        <p className="text-muted">Targets, budget and approved instruments were supplied for this illustration.</p>
      )}
      {result.exposures.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Current weight against the supplied target</caption>
            <thead>
              <tr className="text-muted">
                <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Class</th>
                <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Current</th>
                <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Target</th>
                <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Position</th>
                <th className="py-[var(--space-2)] font-medium">New cash</th>
              </tr>
            </thead>
            <tbody>
              {result.exposures.map((row) => (
                <tr key={row.assetClass} className="border-t border-border">
                  <td className="py-[var(--space-2)] pr-[var(--space-3)]">{CLASS_LABELS[row.assetClass]}</td>
                  <td className="py-[var(--space-2)] pr-[var(--space-3)] aq-num">{weight(row.currentWeightBps)}</td>
                  <td className="py-[var(--space-2)] pr-[var(--space-3)] aq-num">{weight(row.targetWeightBps)}</td>
                  <td className="py-[var(--space-2)] pr-[var(--space-3)]">{row.side}</td>
                  <td className="py-[var(--space-2)] aq-num">
                    {formatMinor(row.deploymentMinor, result.reportingCurrency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {result.instruments.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Whole units that fit the supplied budget</caption>
            <thead>
              <tr className="text-muted">
                <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Instrument</th>
                <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Units</th>
                <th className="py-[var(--space-2)] font-medium">Spend</th>
              </tr>
            </thead>
            <tbody>
              {result.instruments.map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="py-[var(--space-2)] pr-[var(--space-3)]">{row.name}</td>
                  <td className="py-[var(--space-2)] pr-[var(--space-3)]">
                    {row.status === "planned" ? row.units?.toString() : row.reason}
                  </td>
                  <td className="py-[var(--space-2)] aq-num">
                    {row.spendMinor === null ? "Unavailable" : formatMinor(row.spendMinor, result.reportingCurrency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {result.unallocatedMinor !== null ? (
        <p className="text-muted">
          Unallocated after whole units: {formatMinor(result.unallocatedMinor, result.reportingCurrency)}. No order is sent.
        </p>
      ) : null}
    </div>
  );
}

export function DeployCapitalPanel() {
  const exampleResult = deployCapital(exampleDeployment);
  const unconfiguredResult = deployCapital(unconfiguredDeployment);
  return (
    <div className="grid gap-[var(--space-6)]" data-testid="deploy-capital">
      <section className="grid gap-[var(--space-3)]">
        <h1 className="aq-page-title">Deploy capital</h1>
        <p className="text-muted">
          This is a read-only illustration. It does not read your Saxo account, and it will not place a trade.
        </p>
      </section>
      <section className="grid gap-[var(--space-3)]" data-testid="deploy-example">
        <h2 className="text-foreground">Example allocation</h2>
        <p className="text-muted">
          The amounts below are made up so the calculation can be inspected. They are not your holdings.
        </p>
        <ResultTable result={exampleResult} />
      </section>
      <section className="grid gap-[var(--space-3)]" data-testid="deploy-unconfigured">
        <h2 className="text-foreground">Your preferences</h2>
        <ResultTable result={unconfiguredResult} />
      </section>
    </div>
  );
}
