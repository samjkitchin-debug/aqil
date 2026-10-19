import type { BrokerPortfolioView } from "../saxo/portfolio.ts";
import { parseMajorToMinor } from "../wealth/money.ts";
import type { InvestableClass, Target } from "../wealth/allocation.ts";
import type { ApprovedInstrument, ClassValue, DeployCapitalInput, FxRate } from "./deploy.ts";

export type SavedPreferences = {
  targets: readonly Target[] | null;
  fx: readonly FxRate[];
  instruments: readonly ApprovedInstrument[] | null;
  additionalCashMinor: bigint | null;
};

export type ObservedHolding = {
  name: string;
  valueLabel: string;
  reason: string;
};

export type PortfolioDeployment = {
  available: boolean;
  canCalculate: boolean;
  retrievedAt: string | null;
  environment: BrokerPortfolioView["environment"] | null;
  input: DeployCapitalInput;
  observedHoldings: ObservedHolding[];
  limitations: string[];
};

const EMPTY: DeployCapitalInput = {
  reportingCurrency: "SGD",
  classValues: [],
  targets: null,
  additionalCashMinor: null,
  instruments: null,
  fx: [],
};

function minor(amount: string | null, currency: string): bigint | null {
  if (amount === null) return null;
  try {
    return parseMajorToMinor(amount, currency);
  } catch {
    return null;
  }
}

/**
 * Uses Saxo-reported cash only. Holdings stay unclassified, so they are listed
 * and omitted from the class totals. Buying power is not cash.
 * Targets, budget, approved instruments and FX come only from saved preferences.
 */
export function deploymentFromPortfolio(
  broker: BrokerPortfolioView | null,
  preferences: SavedPreferences,
): PortfolioDeployment {
  if (!broker) {
    return {
      available: false,
      canCalculate: false,
      retrievedAt: null,
      environment: null,
      input: { ...EMPTY, targets: preferences.targets, fx: preferences.fx, instruments: preferences.instruments, additionalCashMinor: preferences.additionalCashMinor },
      observedHoldings: [],
      limitations: ["No saved Saxo snapshot is available."],
    };
  }

  const limitations: string[] = [];
  const currencies = [...new Set(broker.accounts.map((account) => account.currency).filter((currency): currency is string => Boolean(currency)))];
  const reportingCurrency = currencies.length === 1 ? currencies[0] : null;
  if (!reportingCurrency) {
    limitations.push("The saved accounts do not share one currency, so no reporting currency is assumed.");
  }

  const classValues: ClassValue[] = [];
  if (reportingCurrency) {
    let cash = BigInt(0);
    let sawCash = false;
    for (const account of broker.accounts) {
      if (account.currency !== reportingCurrency || account.cashBalance === null) continue;
      const amount = minor(account.cashBalance, reportingCurrency);
      if (amount === null) {
        limitations.push(`Cash on ${account.label} could not be read in ${reportingCurrency}.`);
        continue;
      }
      sawCash = true;
      cash += amount;
    }
    if (sawCash) {
      classValues.push({ assetClass: "cash_investable" satisfies InvestableClass, currency: reportingCurrency, amountMinor: cash });
    }
  }

  const observedHoldings = broker.holdings.map((holding) => ({
    name: holding.name,
    valueLabel: holding.marketValue === null ? "Unavailable" : `${holding.marketValue} ${holding.currency ?? ""}`.trim(),
    reason: "Unclassified, so it is not included in the class calculation.",
  }));
  if (observedHoldings.length > 0) {
    limitations.push("Saved holdings are unclassified. They are shown, and they are not assigned to an asset class.");
  }

  return {
    available: true,
    canCalculate: reportingCurrency !== null,
    retrievedAt: broker.retrievedAt,
    environment: broker.environment,
    input: {
      reportingCurrency: reportingCurrency ?? "",
      classValues: reportingCurrency ? classValues : [],
      targets: preferences.targets,
      additionalCashMinor: preferences.additionalCashMinor,
      instruments: preferences.instruments,
      fx: preferences.fx,
    },
    observedHoldings,
    limitations,
  };
}
