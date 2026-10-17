"use client";

import { useMemo, useState } from "react";

import {
  allocateContributionToTargets,
  computePortfolioAnalytics,
} from "@/lib/wealth/analytics";
import { formatMinor, minorFromDecimal } from "@/lib/wealth/minor-units";
import { fromWire, type WealthSnapshotWire } from "@/lib/wealth/serialize";

type Props = {
  snapshot: WealthSnapshotWire;
};

const SCENARIO_TARGETS = [
  { label: "Strategic plan (saved)", key: "saved" as const },
  { label: "Explore: more global equity", key: "global_heavy" as const },
  { label: "Explore: more bonds", key: "bond_heavy" as const },
];

export function ContributionScenarioPanel({ snapshot }: Props) {
  const base = useMemo(() => fromWire(snapshot), [snapshot]);
  const [scenarioKey, setScenarioKey] = useState<"saved" | "global_heavy" | "bond_heavy">("saved");
  const [amountInput, setAmountInput] = useState(
    base.contributionPlan
      ? (Number(base.contributionPlan.amountMinor) / 100).toFixed(2)
      : "5000.00",
  );

  const scenarioTargets = useMemo(() => {
    if (scenarioKey === "saved") return base.targets;
    if (scenarioKey === "global_heavy") {
      return [
        { assetClass: "global_equity" as const, targetWeightBps: 8500 },
        { assetClass: "thematic_technology" as const, targetWeightBps: 0 },
        { assetClass: "investment_grade_bonds" as const, targetWeightBps: 1500 },
      ];
    }
    return [
      { assetClass: "global_equity" as const, targetWeightBps: 5500 },
      { assetClass: "thematic_technology" as const, targetWeightBps: 0 },
      { assetClass: "investment_grade_bonds" as const, targetWeightBps: 4500 },
    ];
  }, [base.targets, scenarioKey]);

  const analytics = useMemo(
    () =>
      computePortfolioAnalytics(
        base.positions,
        scenarioTargets,
        base.profile.emergencyReserveMinor,
      ),
    [base.positions, base.profile.emergencyReserveMinor, scenarioTargets],
  );

  let allocation: ReturnType<typeof allocateContributionToTargets> | null = null;
  let parseError: string | null = null;
  try {
    const minor = minorFromDecimal(amountInput);
    allocation = allocateContributionToTargets(minor, analytics);
  } catch {
    parseError = "Enter a valid contribution amount with up to two decimal places.";
  }

  return (
    <section className="wealth-panel" data-testid="contribution-scenario">
      <h3 className="wealth-section-title">Next contribution scenario</h3>
      <p className="wealth-body">
        Explore allocation of the next contribution. Scenarios do not change your saved strategic
        plan until you explicitly update targets in a future editor.
      </p>
      <label className="wealth-field">
        <span className="wealth-meta">Contribution amount ({base.profile.baseCurrency})</span>
        <input
          className="wealth-input"
          value={amountInput}
          onChange={(event) => setAmountInput(event.target.value)}
          inputMode="decimal"
        />
      </label>
      <fieldset className="wealth-scenario-options">
        <legend className="wealth-meta">Strategic mix (explore only)</legend>
        {SCENARIO_TARGETS.map((option) => (
          <label key={option.key} className="wealth-radio">
            <input
              type="radio"
              name="wealth-scenario"
              checked={scenarioKey === option.key}
              onChange={() => setScenarioKey(option.key)}
            />
            {option.label}
          </label>
        ))}
      </fieldset>
      {parseError ? (
        <p className="wealth-warning">{parseError}</p>
      ) : allocation ? (
        <>
          <ul className="wealth-allocation-list">
            {[...allocation.perClassMinor.entries()].map(([assetClass, minor]) => (
              <li key={assetClass}>
                <span className="wealth-meta">{assetClass.replaceAll("_", " ")}</span>
                <span>{formatMinor(minor, base.profile.baseCurrency)}</span>
              </li>
            ))}
          </ul>
          {allocation.contributionsInsufficient ? (
            <p className="wealth-warning" data-testid="contributions-insufficient">
              This contribution alone is unlikely to bring all asset classes back within a tight band
              around target. Larger or additional contributions may be needed.
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
