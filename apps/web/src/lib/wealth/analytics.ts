import type { AllocationTarget, AssetClass, WealthPosition } from "./types";
import { allocateByWeightsBps, sumMinor } from "./minor-units";

export type ClassWeight = {
  assetClass: AssetClass;
  actualBps: number;
  targetBps: number | null;
  driftBps: number | null;
  valueMinor: bigint;
};

export type PortfolioAnalytics = {
  investableTotalMinor: bigint;
  emergencyReserveMinor: bigint;
  classWeights: ClassWeight[];
  largestFund: {
    positionId: string;
    name: string;
    concentrationBps: number;
    valueMinor: bigint;
  } | null;
  thematicExposure: { label: string; valueMinor: bigint; bps: number }[];
  targetsSumBps: number;
  targetsComplete: boolean;
  missingData: boolean;
};

export function computePortfolioAnalytics(
  positions: readonly WealthPosition[],
  targets: readonly AllocationTarget[],
  emergencyReserveMinor: bigint,
): PortfolioAnalytics {
  const investableTotalMinor = sumMinor(positions.map((p) => p.marketValueMinor));
  const totalForConcentration = investableTotalMinor > 0n ? investableTotalMinor : 0n;

  const byClass = new Map<AssetClass, bigint>();
  for (const position of positions) {
    byClass.set(
      position.assetClass,
      (byClass.get(position.assetClass) ?? 0n) + position.marketValueMinor,
    );
  }

  const targetMap = new Map(targets.map((t) => [t.assetClass, t.targetWeightBps]));
  const targetsSumBps = targets.reduce((acc, t) => acc + t.targetWeightBps, 0);
  const targetsComplete = targets.length > 0 && targetsSumBps === 10000;

  const classWeights: ClassWeight[] = [];
  const classes = new Set<AssetClass>([...byClass.keys(), ...targetMap.keys()]);
  for (const assetClass of classes) {
    const valueMinor = byClass.get(assetClass) ?? 0n;
    const actualBps =
      totalForConcentration > 0n
        ? Number((valueMinor * 10000n) / totalForConcentration)
        : 0;
    const targetBps = targetMap.get(assetClass) ?? null;
    const driftBps = targetBps === null ? null : actualBps - targetBps;
    classWeights.push({ assetClass, actualBps, targetBps, driftBps, valueMinor });
  }
  classWeights.sort((a, b) => a.assetClass.localeCompare(b.assetClass));

  let largestFund: PortfolioAnalytics["largestFund"] = null;
  for (const position of positions) {
    const bps =
      totalForConcentration > 0n
        ? Number((position.marketValueMinor * 10000n) / totalForConcentration)
        : 0;
    if (!largestFund || bps > largestFund.concentrationBps) {
      largestFund = {
        positionId: position.id,
        name: position.name,
        concentrationBps: bps,
        valueMinor: position.marketValueMinor,
      };
    }
  }

  const thematic = new Map<string, bigint>();
  for (const position of positions) {
    if (!position.thematicLabel) continue;
    thematic.set(
      position.thematicLabel,
      (thematic.get(position.thematicLabel) ?? 0n) + position.marketValueMinor,
    );
  }
  const thematicExposure = [...thematic.entries()].map(([label, valueMinor]) => ({
    label,
    valueMinor,
    bps:
      totalForConcentration > 0n
        ? Number((valueMinor * 10000n) / totalForConcentration)
        : 0,
  }));

  const missingData = positions.some((p) => !p.valuationDate || p.marketValueMinor < 0n);

  return {
    investableTotalMinor,
    emergencyReserveMinor,
    classWeights,
    largestFund,
    thematicExposure,
    targetsSumBps,
    targetsComplete,
    missingData,
  };
}

export type ContributionAllocationResult = {
  perClassMinor: Map<AssetClass, bigint>;
  totalMinor: bigint;
  remainingDriftBps: ClassWeight[];
  contributionsInsufficient: boolean;
};

/** Allocate next contribution toward underweight classes; does not mutate targets. */
export function allocateContributionToTargets(
  contributionMinor: bigint,
  analytics: PortfolioAnalytics,
): ContributionAllocationResult {
  if (contributionMinor <= 0n) {
    throw new Error("contribution must be positive");
  }
  const underweights = analytics.classWeights
    .filter((row) => row.targetBps !== null && row.driftBps !== null && row.driftBps < 0)
    .map((row) => ({
      key: row.assetClass,
      bps: Math.max(1, -(row.driftBps ?? 0)),
    }));

  const weights =
    underweights.length > 0
      ? underweights
      : analytics.classWeights
          .filter((row) => row.targetBps !== null && (row.targetBps ?? 0) > 0)
          .map((row) => ({ key: row.assetClass, bps: row.targetBps ?? 0 }));

  if (weights.length === 0) {
    return {
      perClassMinor: new Map(),
      totalMinor: contributionMinor,
      remainingDriftBps: analytics.classWeights,
      contributionsInsufficient: true,
    };
  }

  const raw = allocateByWeightsBps(
    contributionMinor,
    weights.map((w) => ({ key: w.key, bps: w.bps })),
  );
  const perClassMinor = new Map<AssetClass, bigint>();
  for (const [key, value] of raw) {
    perClassMinor.set(key as AssetClass, value);
  }

  const projected = new Map<AssetClass, bigint>();
  for (const row of analytics.classWeights) {
    projected.set(row.assetClass, row.valueMinor + (perClassMinor.get(row.assetClass) ?? 0n));
  }
  const projectedTotal = sumMinor([...projected.values()]);
  const remainingDriftBps: ClassWeight[] = analytics.classWeights.map((row) => {
    const valueMinor = projected.get(row.assetClass) ?? 0n;
    const actualBps =
      projectedTotal > 0n ? Number((valueMinor * 10000n) / projectedTotal) : 0;
    const targetBps = row.targetBps;
    const driftBps = targetBps === null ? null : actualBps - targetBps;
    return { ...row, actualBps, driftBps, valueMinor };
  });

  const maxDrift = remainingDriftBps.reduce(
    (acc, row) => Math.max(acc, Math.abs(row.driftBps ?? 0)),
    0,
  );

  return {
    perClassMinor,
    totalMinor: contributionMinor,
    remainingDriftBps,
    contributionsInsufficient: maxDrift > 200,
  };
}

/** Research payloads must never change strategic targets (explicit guard for tests). */
export function applyResearchInsightToTargets(
  targets: readonly AllocationTarget[],
  research: { thematic?: string; sentiment?: string },
): AllocationTarget[] {
  void research;
  return targets.map((row) => ({ ...row }));
}
