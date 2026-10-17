export type AssetClass =
  | "global_equity"
  | "thematic_technology"
  | "investment_grade_bonds"
  | "cash_investable";

export type WealthPosition = {
  id: string;
  isin: string | null;
  symbol: string | null;
  name: string;
  assetClass: AssetClass;
  thematicLabel: string | null;
  currency: string;
  marketValueMinor: bigint;
  valuationDate: string;
};

export type AllocationTarget = {
  assetClass: AssetClass;
  targetWeightBps: number;
};

export type ContributionPlan = {
  amountMinor: bigint;
  currency: string;
  cadence: "monthly";
  dayOfMonth: number | null;
};

export type ContributionEvent = {
  id: string;
  occurredAt: string;
  amountMinor: bigint;
  currency: string;
  note: string | null;
};

export type WealthProfile = {
  baseCurrency: string;
  emergencyReserveMinor: bigint;
};

export type WealthSnapshot = {
  source: "database" | "fixture";
  profile: WealthProfile;
  positions: WealthPosition[];
  targets: AllocationTarget[];
  contributionPlan: ContributionPlan | null;
  contributionHistory: ContributionEvent[];
  dataFreshness: {
    oldestValuationDate: string | null;
    missingValuationCount: number;
  };
};
