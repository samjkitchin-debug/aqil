import { BrokerSection, saxoErrorMessage } from "@/components/wealth/broker-section";
import { createAccount, recordHolding, saveTargets } from "@/lib/wealth/actions";
import { consolidate, liveInvestable, monetaryGaps, type Target } from "@/lib/wealth/allocation";
import { convertMinor, formatMinor } from "@/lib/wealth/money";
import type { WealthLoad } from "@/lib/wealth/load-snapshot";

const CLASSES = [
  ["global_equity", "Global equity"],
  ["thematic_technology", "Thematic technology"],
  ["investment_grade_bonds", "Investment-grade bonds"],
  ["cash_investable", "Investable cash"],
  ["emergency_reserve", "Emergency reserve"],
] as const;

function label(assetClass: string): string {
  return CLASSES.find(([value]) => value === assetClass)?.[1] ?? assetClass;
}

export function MyWealthView({
  load,
  error,
  connectEnabled,
}: {
  load: WealthLoad;
  error: string | null;
  connectEnabled: boolean;
}) {
  const broker = load.status === "unauthorized" ? null : load.broker;
  if (load.status === "storage_pending") {
    return (
      <div data-testid="wealth-pending">
        <BrokerSection broker={broker} error={error} connectEnabled={connectEnabled} heading="h1" />
      </div>
    );
  }

  const snapshot = load.status === "ok" ? load.snapshot : null;
  const holdings = snapshot?.holdings ?? [];
  const live = liveInvestable(
    holdings.map((holding) => ({
      assetClass: holding.assetClass,
      environment: holding.environment,
      currency: holding.currency,
      amountMinor: holding.amountMinor,
    })),
  );
  const reporting = snapshot?.reportingCurrency ?? "SGD";
  const total = snapshot
    ? consolidate(live, reporting, snapshot.fx, convertMinor)
    : { status: "unavailable" as const, reason: "no holdings yet" };
  const classValues = new Map<Target["assetClass"], bigint>();
  for (const holding of live) {
    if (holding.assetClass === "emergency_reserve" || holding.currency !== reporting) continue;
    const key = holding.assetClass;
    classValues.set(key, (classValues.get(key) ?? BigInt(0)) + holding.amountMinor);
  }
  const targets = (snapshot?.targets ?? []).filter(
    (target): target is Target => target.assetClass !== "emergency_reserve",
  );
  const gaps =
    targets.length > 0 && targets.reduce((sum, target) => sum + target.targetWeightBps, 0) === 10000
      ? monetaryGaps(
          [...classValues.entries()].map(([assetClass, currentMinor]) => ({ assetClass, currentMinor })),
          targets,
          BigInt(0),
        )
      : [];
  const showRecorded = !broker || holdings.length > 0 || (snapshot?.accounts.length ?? 0) > 0;

  return (
    <div className="grid gap-[var(--space-6)]">
      {broker ? <BrokerSection broker={broker} error={error} connectEnabled={connectEnabled} heading="h1" /> : null}
      {showRecorded ? (
        <>
      <section>
        {broker ? (
          <h2 className="font-semibold text-foreground">Recorded outside Saxo</h2>
        ) : (
          <h1 className="aq-page-title">My wealth</h1>
        )}
        <p className="mt-[var(--space-3)] text-muted">
          {total.status === "total"
            ? `Recorded investable total ${formatMinor(total.amountMinor, total.currency)}. Emergency reserves are excluded.`
            : "A combined total of recorded accounts is unavailable. Native amounts are shown separately."}
        </p>
        {broker ? null : <BrokerSection broker={broker} error={error} connectEnabled={connectEnabled} heading="h2" />}
        {error && !saxoErrorMessage(error) ? <p className="mt-[var(--space-3)] text-foreground">That entry could not be saved.</p> : null}
        {snapshot && snapshot.quarantined.length > 0 ? (
          <p className="mt-[var(--space-3)] text-foreground">
            Some holdings have an unknown classification and are not included.
          </p>
        ) : null}
      </section>

      {holdings.length === 0 && !broker ? (
        <p data-testid="wealth-empty" className="text-muted">
          No holdings are recorded for this account.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Current holdings</caption>
            <thead>
              <tr className="text-muted">
                <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Holding</th>
                <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Account</th>
                <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Class</th>
                <th className="py-[var(--space-2)] font-medium">Value</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
                <tr key={holding.id} className="border-t border-border">
                  <td className="py-[var(--space-2)] pr-[var(--space-3)]">{holding.name}</td>
                  <td className="py-[var(--space-2)] pr-[var(--space-3)]">
                    {holding.accountName}
                    {holding.environment === "simulation" ? " (simulation)" : ""}
                  </td>
                  <td className="py-[var(--space-2)] pr-[var(--space-3)]">{label(holding.assetClass)}</td>
                  <td className="py-[var(--space-2)]">
                    {formatMinor(holding.amountMinor, holding.currency)} as of {holding.asOf}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {gaps.length > 0 ? (
        <section>
          <h2 className="font-semibold text-foreground">Drift from your targets</h2>
          <ul className="mt-[var(--space-3)] text-muted">
            {gaps.map((gap) => (
              <li key={gap.assetClass}>
                {label(gap.assetClass)}: {formatMinor(gap.gapMinor, reporting)} versus target
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="grid gap-[var(--space-4)]">
        <h2 className="font-semibold text-foreground">Add an account</h2>
        <form action={createAccount} className="grid max-w-prose gap-[var(--space-3)]">
          <label className="text-sm text-muted">
            Name
            <input name="name" required className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]" />
          </label>
          <label className="text-sm text-muted">
            Provider
            <select name="provider" className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]">
              <option value="manual">Manual</option>
              <option value="cash">Cash</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className="text-sm text-muted">
            Environment
            <select name="environment" className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]">
              <option value="live">Live</option>
              <option value="simulation">Simulation</option>
            </select>
          </label>
          <label className="text-sm text-muted">
            Currency
            <input name="currency" defaultValue="SGD" required className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]" />
          </label>
          <button type="submit" className="w-fit rounded-lg bg-brand-navy px-[var(--space-4)] py-[var(--space-2)] text-inverse">
            Save account
          </button>
        </form>
      </section>

      {snapshot && snapshot.accounts.length > 0 ? (
        <section className="grid gap-[var(--space-4)]">
          <h2 className="font-semibold text-foreground">Record a holding</h2>
          <form action={recordHolding} className="grid max-w-prose gap-[var(--space-3)]">
            <label className="text-sm text-muted">
              Account
              <select name="account_id" className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]">
                {snapshot.accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm text-muted">
              Name
              <input name="name" required className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]" />
            </label>
            <label className="text-sm text-muted">
              ISIN, if you have one
              <input name="isin" className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]" />
            </label>
            <label className="text-sm text-muted">
              Classification
              <select name="asset_class" className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]">
                {CLASSES.map(([value, text]) => (
                  <option key={value} value={value}>
                    {text}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm text-muted">
              Quantity
              <input name="quantity" required defaultValue="1" className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]" />
            </label>
            <label className="text-sm text-muted">
              Value and currency
              <span className="mt-[var(--space-1)] flex gap-[var(--space-2)]">
                <input name="amount" required inputMode="decimal" className="w-full border border-border bg-surface p-[var(--space-2)]" />
                <input name="currency" defaultValue="SGD" required className="w-24 border border-border bg-surface p-[var(--space-2)]" />
              </span>
            </label>
            <label className="text-sm text-muted">
              Valuation date
              <input name="as_of" type="date" required className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]" />
            </label>
            <button type="submit" className="w-fit rounded-lg bg-brand-navy px-[var(--space-4)] py-[var(--space-2)] text-inverse">
              Save holding
            </button>
          </form>
        </section>
      ) : null}

      <section className="grid max-w-prose gap-[var(--space-3)]">
        <h2 className="font-semibold text-foreground">Strategic targets</h2>
        <p className="text-muted">Enter percentages that add up to 100. They are not adjusted for you.</p>
        <form action={saveTargets} className="grid gap-[var(--space-3)]">
          {CLASSES.filter(([value]) => value !== "emergency_reserve").map(([value, text]) => (
            <label key={value} className="text-sm text-muted">
              {text} (%)
              <input name={value} inputMode="numeric" defaultValue="0" className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]" />
            </label>
          ))}
          <button type="submit" className="w-fit rounded-lg bg-brand-navy px-[var(--space-4)] py-[var(--space-2)] text-inverse">
            Save targets
          </button>
        </form>
      </section>
        </>
      ) : null}
    </div>
  );
}
