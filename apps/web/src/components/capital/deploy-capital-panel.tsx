import { deployCapital, type ClassExposure, type DeployCapitalResult, type FxRate } from "@/lib/capital/deploy";
import { exampleDeployment } from "@/lib/capital/example";
import { deploymentFromPortfolio, type PortfolioDeployment } from "@/lib/capital/from-portfolio";
import { brokerHoldingKey } from "@/lib/capital/holding-key";
import { saveInvestmentPolicy } from "@/lib/capital/policy-actions";
import type { LoadedInvestmentPolicy } from "@/lib/capital/policy-file";
import { formatRetrievedAt, type BrokerPortfolioView } from "@/lib/saxo/portfolio";
import { formatMinor } from "@/lib/wealth/money";

const CLASS_LABELS: Record<ClassExposure["assetClass"], string> = {
  global_equity: "Global equity",
  thematic_technology: "Thematic technology",
  investment_grade_bonds: "Investment-grade bonds",
  cash_investable: "Investable cash",
};

const TARGET_FIELDS = [
  ["global_equity", "Global equity"],
  ["thematic_technology", "Thematic technology"],
  ["investment_grade_bonds", "Investment-grade bonds"],
  ["cash_investable", "Investable cash"],
] as const;

const INSTRUMENT_SLOTS = 3;

function weight(bps: number): string {
  const whole = Math.trunc(bps / 100);
  const fraction = Math.abs(bps % 100).toString().padStart(2, "0");
  return `${whole}.${fraction}%`;
}

function ResultTable({ result, completeNote }: { result: DeployCapitalResult; completeNote: string }) {
  return (
    <div className="grid gap-[var(--space-4)]">
      {result.missing.length > 0 ? (
        <p>Not configured: {result.missing.join(", ")}.</p>
      ) : (
        <p className="text-muted">{completeNote}</p>
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

function instrumentDefaults(policy: LoadedInvestmentPolicy, index: number) {
  const row = policy.form.instruments[index];
  return {
    id: row?.id ?? "",
    name: row?.name ?? "",
    assetClass: row?.assetClass ?? "global_equity",
    currency: row?.currency ?? "SGD",
    minimumUnit: row?.minimumUnit ?? "1",
    priceMajor: row?.priceMajor ?? "",
    costMajorPerUnit: row?.costMajorPerUnit ?? "",
  };
}

export function DeployCapitalPanel({
  broker,
  fx,
  policy,
}: {
  broker: BrokerPortfolioView | null;
  fx: readonly FxRate[];
  policy: LoadedInvestmentPolicy;
}) {
  const preferences = {
    targets: policy.runtime.targets,
    fx,
    instruments: policy.runtime.instruments,
    additionalCashMinor: policy.runtime.additionalCashMinor,
    holdingClasses: policy.runtime.holdingClasses,
  };
  const account: PortfolioDeployment = deploymentFromPortfolio(broker, preferences);
  const accountResult = account.canCalculate ? deployCapital(account.input) : null;
  const exampleResult = deployCapital(exampleDeployment);
  const instrumentCount = Math.max(INSTRUMENT_SLOTS, policy.form.instruments.length);
  return (
    <div className="grid gap-[var(--space-6)]" data-testid="deploy-capital">
      <section className="grid gap-[var(--space-3)]">
        <h1 className="aq-page-title">Deploy capital</h1>
        <p className="text-muted">
          Read only. Reported cash from the saved Saxo snapshot can be used. Holdings stay unclassified until you classify them. No order is sent.
        </p>
      </section>
      <section className="grid max-w-prose gap-[var(--space-3)]" data-testid="deploy-policy">
        <h2 className="text-foreground">Investment policy</h2>
        <p className="text-muted">
          Saved on this device for your sign-in only. Percentages must add up to 100. Leave the budget blank if you have not set one.
        </p>
        <form action={saveInvestmentPolicy} className="grid gap-[var(--space-4)]">
          {TARGET_FIELDS.map(([field, label]) => (
            <label key={field} className="text-sm text-muted">
              {label} (%)
              <input
                name={field}
                inputMode="decimal"
                defaultValue={policy.form[field]}
                className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
              />
            </label>
          ))}
          <label className="text-sm text-muted">
            Additional cash to deploy
            <input
              name="additional_cash"
              inputMode="decimal"
              defaultValue={policy.form.additionalCashMajor}
              placeholder="Leave blank if not set"
              className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
            />
          </label>
          <div className="grid gap-[var(--space-3)]">
            <h3 className="text-sm font-medium text-foreground">Approved instruments</h3>
            <p className="text-sm text-muted">Optional. Whole units only. Cost is included only when you enter it.</p>
            <input type="hidden" name="instrument_count" value={instrumentCount} />
            {Array.from({ length: instrumentCount }, (_, index) => {
              const defaults = instrumentDefaults(policy, index);
              return (
                <fieldset key={index} className="grid gap-[var(--space-2)] border border-border p-[var(--space-3)]">
                  <legend className="px-[var(--space-1)] text-sm text-muted">Instrument {index + 1}</legend>
                  <label className="text-sm text-muted">
                    Id
                    <input
                      name={`instrument_id_${index}`}
                      defaultValue={defaults.id}
                      className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
                    />
                  </label>
                  <label className="text-sm text-muted">
                    Name
                    <input
                      name={`instrument_name_${index}`}
                      defaultValue={defaults.name}
                      className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
                    />
                  </label>
                  <label className="text-sm text-muted">
                    Asset class
                    <select
                      name={`instrument_asset_class_${index}`}
                      defaultValue={defaults.assetClass}
                      className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
                    >
                      {TARGET_FIELDS.map(([value, text]) => (
                        <option key={value} value={value}>
                          {text}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm text-muted">
                    Currency
                    <input
                      name={`instrument_currency_${index}`}
                      defaultValue={defaults.currency}
                      className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
                    />
                  </label>
                  <label className="text-sm text-muted">
                    Minimum unit
                    <input
                      name={`instrument_minimum_unit_${index}`}
                      defaultValue={defaults.minimumUnit}
                      className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
                    />
                  </label>
                  <label className="text-sm text-muted">
                    Price
                    <input
                      name={`instrument_price_${index}`}
                      inputMode="decimal"
                      defaultValue={defaults.priceMajor}
                      className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
                    />
                  </label>
                  <label className="text-sm text-muted">
                    Cost per unit (optional)
                    <input
                      name={`instrument_cost_${index}`}
                      inputMode="decimal"
                      defaultValue={defaults.costMajorPerUnit}
                      className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
                    />
                  </label>
                </fieldset>
              );
            })}
          </div>
          {broker && broker.holdings.length > 0 ? (
            <div className="grid gap-[var(--space-3)]">
              <h3 className="text-sm font-medium text-foreground">Snapshot holdings</h3>
              <p className="text-sm text-muted">Assign a class to include a line in the calculation. Unassigned lines stay out of the class total.</p>
              <ul className="grid gap-[var(--space-3)]">
                {broker.holdings.map((holding) => {
                  const key = brokerHoldingKey(holding);
                  const fieldName = `holding_class__${encodeURIComponent(key)}`;
                  return (
                    <li key={key} className="grid gap-[var(--space-2)] border border-border p-[var(--space-3)]">
                      <p className="text-sm text-foreground">{holding.name}</p>
                      <label className="text-sm text-muted">
                        Asset class
                        <select
                          name={fieldName}
                          defaultValue={policy.form.holdingClasses[key] ?? ""}
                          className="mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]"
                        >
                          <option value="">Unclassified</option>
                          {TARGET_FIELDS.map(([value, text]) => (
                            <option key={value} value={value}>
                              {text}
                            </option>
                          ))}
                        </select>
                      </label>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
          <button type="submit" className="w-fit rounded-lg bg-brand-navy px-[var(--space-4)] py-[var(--space-2)] text-inverse">
            Save investment policy
          </button>
        </form>
      </section>
      <section className="grid gap-[var(--space-3)]" data-testid="deploy-account">
        <h2 className="text-foreground">Saved snapshot</h2>
        {account.available ? (
          <p className="text-muted">
            {account.environment === "simulation" ? "Simulation account" : "Live account"}. Last retrieved{" "}
            {account.retrievedAt ? formatRetrievedAt(account.retrievedAt) : "at an unknown time"}.
          </p>
        ) : (
          <p className="text-muted">No saved Saxo snapshot is available for this sign-in.</p>
        )}
        {account.limitations.map((limitation) => (
          <p key={limitation} className="text-muted">{limitation}</p>
        ))}
        {account.observedHoldings.length > 0 ? (
          <ul className="grid gap-[var(--space-2)]">
            {account.observedHoldings.map((holding, index) => (
              <li key={`${holding.name}-${index}`}>
                {holding.name}: {holding.valueLabel}. {holding.reason}
              </li>
            ))}
          </ul>
        ) : null}
        {accountResult ? (
          <ResultTable
            result={accountResult}
            completeNote="The saved snapshot and the saved investment policy were both present."
          />
        ) : null}
      </section>
      <section className="grid gap-[var(--space-3)]" data-testid="deploy-example">
        <h2 className="text-foreground">Example allocation</h2>
        <p className="text-muted">
          The amounts below are made up so the calculation can be inspected. They are not your holdings.
        </p>
        <ResultTable result={exampleResult} completeNote="This example supplied its own targets, budget and instrument." />
      </section>
    </div>
  );
}
