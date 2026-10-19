import {
  ILLUSTRATION_DISCLAIMER,
  formatIllustrationMajor,
  formatIllustrationRate,
  runCompoundingIllustration,
  type CompoundingScenarioResult,
} from "@/lib/learn/compounding";

function ScenarioBlock({ scenario, feeRate, inflationRate }: {
  scenario: CompoundingScenarioResult;
  feeRate: number;
  inflationRate: number;
}) {
  return (
    <section
      className="research-banner"
      data-testid={`learn-compounding-${scenario.key}`}
      aria-labelledby={`learn-scenario-${scenario.key}-title`}
    >
      <h2 className="research-headline" id={`learn-scenario-${scenario.key}-title`}>
        {scenario.label}
      </h2>
      <p className="research-body">
        Assumed gross return {formatIllustrationRate(scenario.grossAnnualReturn)} per year, net of
        an illustrative fee of {formatIllustrationRate(feeRate)} (
        {formatIllustrationRate(scenario.netAnnualReturn)} net). Inflation assumption{" "}
        {formatIllustrationRate(inflationRate)} per year.
      </p>
      <dl className="research-body mt-[var(--space-4)] grid gap-[var(--space-2)]">
        <div>
          <dt>Starting balance (illustration)</dt>
          <dd>{formatIllustrationMajor(scenario.startingBalanceMajor)}</dd>
        </div>
        <div>
          <dt>Regular contributions over the horizon (illustration)</dt>
          <dd>{formatIllustrationMajor(scenario.periodicContributionsMajor)}</dd>
        </div>
        <div>
          <dt>Total paid in (illustration)</dt>
          <dd>{formatIllustrationMajor(scenario.totalPaidInMajor)}</dd>
        </div>
        <div>
          <dt>Growth on investments, net of fees (illustration)</dt>
          <dd>{formatIllustrationMajor(scenario.growthFromInvestmentsMajor)}</dd>
        </div>
        <div>
          <dt>Nominal ending balance (illustration)</dt>
          <dd>{formatIllustrationMajor(scenario.nominalEndingMajor)}</dd>
        </div>
        <div>
          <dt>Inflation-adjusted ending balance (illustration)</dt>
          <dd>{formatIllustrationMajor(scenario.inflationAdjustedEndingMajor)}</dd>
        </div>
        <div>
          <dt>Growth after inflation (illustration)</dt>
          <dd>{formatIllustrationMajor(scenario.growthAfterInflationMajor)}</dd>
        </div>
      </dl>
      <p className="research-meta">{ILLUSTRATION_DISCLAIMER}</p>
    </section>
  );
}

export function CompoundingIllustration() {
  const { input, scenarios } = runCompoundingIllustration();

  return (
    <div data-testid="learn-compounding-illustration">
      <section className="research-banner research-banner--preview" aria-labelledby="learn-intro">
        <p className="research-meta">Compounding laboratory (illustration)</p>
        <h2 className="research-headline" id="learn-intro">
          How contributions and growth can differ
        </h2>
        <p className="research-body">
          This page uses fixed, made-up inputs only. It separates money you pay in from investment
          growth, applies an explicit fee and inflation assumption, and shows a downside case
          alongside base and favourable paths. Past patterns are not a guide to future results.
        </p>
        <p className="research-meta">{ILLUSTRATION_DISCLAIMER}</p>
      </section>

      <section className="max-w-prose" aria-labelledby="learn-assumptions">
        <h2 className="research-section-title" id="learn-assumptions">
          Shared illustration inputs
        </h2>
        <ul className="research-body">
          <li>
            Starting balance (illustration): {formatIllustrationMajor(input.startingBalanceMajor)}
          </li>
          <li>
            Monthly contribution (illustration):{" "}
            {formatIllustrationMajor(input.monthlyContributionMajor)}
          </li>
          <li>Horizon (illustration): {input.horizonYears} years</li>
          <li>
            Annual fee assumption (illustration): {formatIllustrationRate(input.annualFeeRate)}
          </li>
          <li>
            Inflation assumption (illustration):{" "}
            {formatIllustrationRate(input.annualInflationRate)}
          </li>
        </ul>
      </section>

      {scenarios.map((scenario) => (
        <ScenarioBlock
          key={scenario.key}
          scenario={scenario}
          feeRate={input.annualFeeRate}
          inflationRate={input.annualInflationRate}
        />
      ))}
    </div>
  );
}
