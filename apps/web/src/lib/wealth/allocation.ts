export const ASSET_CLASSES = [
  "global_equity",
  "thematic_technology",
  "investment_grade_bonds",
  "cash_investable",
  "emergency_reserve",
] as const;

export type AssetClass = (typeof ASSET_CLASSES)[number];
export type InvestableClass = Exclude<AssetClass, "emergency_reserve">;
export type Environment = "live" | "simulation";

export type Holding = {
  assetClass: AssetClass;
  environment: Environment;
  currency: string;
  amountMinor: bigint;
};

export type Target = {
  assetClass: InvestableClass;
  targetWeightBps: number;
};

const INVESTABLE = new Set<string>([
  "global_equity",
  "thematic_technology",
  "investment_grade_bonds",
  "cash_investable",
]);

export function parseAssetClass(value: string): AssetClass {
  if (!(ASSET_CLASSES as readonly string[]).includes(value)) {
    throw new Error("unknown asset class");
  }
  return value as AssetClass;
}

export function assertTargets(targets: readonly Target[]): void {
  const seen = new Set<string>();
  let total = 0;
  for (const target of targets) {
    if (!INVESTABLE.has(target.assetClass)) {
      throw new Error("unknown asset class");
    }
    if (seen.has(target.assetClass)) {
      throw new Error("duplicate target");
    }
    seen.add(target.assetClass);
    if (!Number.isInteger(target.targetWeightBps) || target.targetWeightBps < 0 || target.targetWeightBps > 10000) {
      throw new Error("invalid target weight");
    }
    total += target.targetWeightBps;
  }
  if (targets.length > 0 && total !== 10000) {
    throw new Error("targets must total 10000 basis points");
  }
}

export function targetsAfterResearch<T extends Target>(targets: readonly T[]): T[] {
  return targets.map((target) => ({ ...target }));
}

export function liveInvestable(holdings: readonly Holding[]): Holding[] {
  return holdings.filter(
    (holding) => holding.environment === "live" && holding.assetClass !== "emergency_reserve",
  );
}

export type Consolidated =
  | { status: "total"; currency: string; amountMinor: bigint }
  | { status: "unavailable"; reason: string };

export function consolidate(
  holdings: readonly Holding[],
  reportingCurrency: string,
  rates: readonly { baseCurrency: string; quoteCurrency: string; rate: string }[],
  convert: (amountMinor: bigint, rate: string) => bigint,
): Consolidated {
  const rows = liveInvestable(holdings);
  if (rows.length === 0) {
    return { status: "unavailable", reason: "no live investable holdings" };
  }
  let total = BigInt(0);
  for (const row of rows) {
    if (row.currency === reportingCurrency) {
      total += row.amountMinor;
      continue;
    }
    const rate = rates.find(
      (item) => item.baseCurrency === row.currency && item.quoteCurrency === reportingCurrency,
    );
    if (!rate) {
      return {
        status: "unavailable",
        reason: `no ${row.currency} to ${reportingCurrency} rate`,
      };
    }
    total += convert(row.amountMinor, rate.rate);
  }
  return { status: "total", currency: reportingCurrency, amountMinor: total };
}

export type Gap = { assetClass: InvestableClass; gapMinor: bigint };

/**
 * gap = target weight × (current investable + external contribution) − current class value.
 * Pass a zero contribution when the cash is already inside current class values.
 */
export function monetaryGaps(
  classValues: readonly { assetClass: InvestableClass; currentMinor: bigint }[],
  targets: readonly Target[],
  externalContributionMinor: bigint,
): Gap[] {
  assertTargets(targets);
  if (externalContributionMinor < BigInt(0)) {
    throw new Error("contribution must not be negative");
  }
  const current = new Map(classValues.map((row) => [row.assetClass, row.currentMinor]));
  const investable = [...current.values()].reduce((sum, value) => sum + value, BigInt(0));
  const base = investable + externalContributionMinor;
  return targets.map((target) => {
    const held = current.get(target.assetClass) ?? BigInt(0);
    const desired = (base * BigInt(target.targetWeightBps)) / BigInt(10000);
    return { assetClass: target.assetClass, gapMinor: desired - held };
  });
}

export function allocateExternalContribution(
  classValues: readonly { assetClass: InvestableClass; currentMinor: bigint }[],
  targets: readonly Target[],
  externalContributionMinor: bigint,
): { assetClass: InvestableClass; amountMinor: bigint }[] {
  if (externalContributionMinor <= BigInt(0)) {
    throw new Error("contribution must be positive");
  }
  const positive = monetaryGaps(classValues, targets, externalContributionMinor).filter(
    (gap) => gap.gapMinor > BigInt(0),
  );
  const gapSum = positive.reduce((sum, gap) => sum + gap.gapMinor, BigInt(0));
  if (gapSum === BigInt(0)) return [];
  const rows = positive.map((gap) => ({
    assetClass: gap.assetClass,
    amountMinor: (externalContributionMinor * gap.gapMinor) / gapSum,
    remainder: (externalContributionMinor * gap.gapMinor) % gapSum,
  }));
  let left =
    externalContributionMinor - rows.reduce((sum, row) => sum + row.amountMinor, BigInt(0));
  rows.sort((a, b) => (a.remainder > b.remainder ? -1 : a.remainder < b.remainder ? 1 : 0));
  for (const row of rows) {
    if (left === BigInt(0)) break;
    row.amountMinor += BigInt(1);
    left -= BigInt(1);
  }
  return rows.map(({ assetClass, amountMinor }) => ({ assetClass, amountMinor }));
}

export function holdingsAfterRefresh<T>(previous: T, outcome: { status: "failed" } | { status: "accepted"; next: T }): T {
  if (outcome.status === "failed") return previous;
  return outcome.next;
}
