export const ILLUSTRATION_DISCLAIMER =
  "Illustration only. Not a forecast, recommendation or guaranteed return.";

export type ScenarioKey = "adverse" | "base" | "favourable";

export type CompoundingScenarioAssumption = {
  key: ScenarioKey;
  label: string;
  /** Gross annual return before fees, as a decimal (for example 0.05). */
  grossAnnualReturn: number;
};

export type CompoundingIllustrationInput = {
  startingBalanceMajor: number;
  monthlyContributionMajor: number;
  horizonYears: number;
  /** Annual ongoing charge, decimal (for example 0.004 for 0.4%). */
  annualFeeRate: number;
  /** Annual inflation, decimal (for example 0.025). */
  annualInflationRate: number;
  scenarios: CompoundingScenarioAssumption[];
};

export type CompoundingScenarioResult = {
  key: ScenarioKey;
  label: string;
  grossAnnualReturn: number;
  netAnnualReturn: number;
  nominalEndingMajor: number;
  startingBalanceMajor: number;
  periodicContributionsMajor: number;
  totalPaidInMajor: number;
  growthFromInvestmentsMajor: number;
  inflationAdjustedEndingMajor: number;
  growthAfterInflationMajor: number;
};

export type CompoundingIllustrationResult = {
  input: CompoundingIllustrationInput;
  scenarios: CompoundingScenarioResult[];
};

export function defaultCompoundingIllustrationInput(): CompoundingIllustrationInput {
  return {
    startingBalanceMajor: 5_000,
    monthlyContributionMajor: 200,
    horizonYears: 20,
    annualFeeRate: 0.004,
    annualInflationRate: 0.025,
    scenarios: [
      { key: "adverse", label: "Downside illustration", grossAnnualReturn: 0.02 },
      { key: "base", label: "Base illustration", grossAnnualReturn: 0.05 },
      { key: "favourable", label: "Favourable illustration", grossAnnualReturn: 0.07 },
    ],
  };
}

export function assertIllustrationInput(input: CompoundingIllustrationInput): void {
  if (input.startingBalanceMajor < 0) {
    throw new Error("starting balance must not be negative");
  }
  if (input.monthlyContributionMajor < 0) {
    throw new Error("monthly contribution must not be negative");
  }
  if (input.horizonYears <= 0 || !Number.isInteger(input.horizonYears)) {
    throw new Error("horizon must be a positive whole number of years");
  }
  if (input.annualFeeRate < 0 || input.annualInflationRate < 0) {
    throw new Error("fee and inflation rates must not be negative");
  }
  if (input.scenarios.length === 0) {
    throw new Error("at least one scenario is required");
  }
}

function netAnnualReturn(gross: number, fee: number): number {
  return gross - fee;
}

function monthlyRateFromAnnual(annual: number): number {
  return (1 + annual) ** (1 / 12) - 1;
}

function roundMajor(amount: number): number {
  return Math.round(amount * 100) / 100;
}

export function projectMonthlyCompounding(
  input: CompoundingIllustrationInput,
  scenario: CompoundingScenarioAssumption,
): CompoundingScenarioResult {
  assertIllustrationInput(input);

  const netAnnual = netAnnualReturn(scenario.grossAnnualReturn, input.annualFeeRate);
  const monthlyRate = monthlyRateFromAnnual(netAnnual);
  const months = input.horizonYears * 12;

  let balance = input.startingBalanceMajor;
  for (let month = 0; month < months; month += 1) {
    balance = balance * (1 + monthlyRate) + input.monthlyContributionMajor;
  }

  const periodicContributions = input.monthlyContributionMajor * months;
  const totalPaidIn = input.startingBalanceMajor + periodicContributions;
  const growth = balance - totalPaidIn;
  const inflationFactor = (1 + input.annualInflationRate) ** input.horizonYears;
  const inflationAdjustedEnding = balance / inflationFactor;
  const growthAfterInflation = inflationAdjustedEnding - totalPaidIn;

  return {
    key: scenario.key,
    label: scenario.label,
    grossAnnualReturn: scenario.grossAnnualReturn,
    netAnnualReturn: netAnnual,
    nominalEndingMajor: roundMajor(balance),
    startingBalanceMajor: roundMajor(input.startingBalanceMajor),
    periodicContributionsMajor: roundMajor(periodicContributions),
    totalPaidInMajor: roundMajor(totalPaidIn),
    growthFromInvestmentsMajor: roundMajor(growth),
    inflationAdjustedEndingMajor: roundMajor(inflationAdjustedEnding),
    growthAfterInflationMajor: roundMajor(growthAfterInflation),
  };
}

export function runCompoundingIllustration(
  input: CompoundingIllustrationInput = defaultCompoundingIllustrationInput(),
): CompoundingIllustrationResult {
  assertIllustrationInput(input);
  return {
    input,
    scenarios: input.scenarios.map((scenario) => projectMonthlyCompounding(input, scenario)),
  };
}

export function formatIllustrationMajor(amount: number): string {
  return new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatIllustrationRate(rate: number): string {
  return new Intl.NumberFormat("en-GB", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(rate);
}
