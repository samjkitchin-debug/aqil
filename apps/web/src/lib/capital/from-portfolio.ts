import type { BrokerPortfolioView } from "../saxo/portfolio.ts";
import { parseMajorToMinor } from "../wealth/money.ts";
import type { InvestableClass, Target } from "../wealth/allocation.ts";
import type { ApprovedInstrument, ClassValue, DeployCapitalInput, FxRate } from "./deploy.ts";
import { brokerHoldingKey } from "./holding-key.ts";
import { toReportingMinor } from "./reporting-value.ts";

export type SavedPreferences = {
  targets: readonly Target[] | null;
  fx: readonly FxRate[];
  instruments: readonly ApprovedInstrument[] | null;
  additionalCashMinor: bigint | null;
  holdingClasses: Readonly<Record<string, InvestableClass>>;
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
 * Uses Saxo-reported cash only. Classified holdings join the class totals when a
 * saved rate exists. Unclassified holdings are listed and omitted. Buying power is not cash.
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

  const reportingByClass = new Map<InvestableClass, bigint>();
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
      reportingByClass.set("cash_investable", cash);
    }
  }

  const observedHoldings: ObservedHolding[] = [];
  let unclassifiedCount = 0;
  for (const holding of broker.holdings) {
    const key = brokerHoldingKey(holding);
    const assigned = preferences.holdingClasses[key];
    const valueLabel =
      holding.marketValue === null ? "Unavailable" : `${holding.marketValue} ${holding.currency ?? ""}`.trim();
    if (!assigned) {
      unclassifiedCount += 1;
      observedHoldings.push({
        name: holding.name,
        valueLabel,
        reason: "Unclassified, so it is not included in the class calculation.",
      });
      continue;
    }
    if (!reportingCurrency) {
      observedHoldings.push({
        name: holding.name,
        valueLabel,
        reason: "No reporting currency is available, so it is not included in the class calculation.",
      });
      continue;
    }
    const currency = holding.currency ?? reportingCurrency;
    const amount = minor(holding.marketValue, currency);
    if (amount === null) {
      observedHoldings.push({
        name: holding.name,
        valueLabel,
        reason: "Market value could not be read, so it is not included in the class calculation.",
      });
      continue;
    }
    const converted = toReportingMinor(amount, currency, reportingCurrency, preferences.fx);
    if (!converted.ok) {
      observedHoldings.push({
        name: holding.name,
        valueLabel,
        reason: `${converted.reason} is not saved, so it is not included in the class calculation.`,
      });
      continue;
    }
    reportingByClass.set(assigned, (reportingByClass.get(assigned) ?? BigInt(0)) + converted.amountMinor);
    observedHoldings.push({
      name: holding.name,
      valueLabel,
      reason: "Classified and included in the class calculation.",
    });
  }
  if (unclassifiedCount > 0) {
    limitations.push("Some saved holdings are unclassified. They are shown, and they are not assigned to an asset class.");
  }

  const classValues: ClassValue[] =
    reportingCurrency !== null
      ? [...reportingByClass.entries()].map(([assetClass, amountMinor]) => ({
          assetClass,
          currency: reportingCurrency,
          amountMinor,
        }))
      : [];

  return {
    available: true,
    canCalculate: reportingCurrency !== null,
    retrievedAt: broker.retrievedAt,
    environment: broker.environment,
    input: {
      reportingCurrency: reportingCurrency ?? "",
      classValues,
      targets: preferences.targets,
      additionalCashMinor: preferences.additionalCashMinor,
      instruments: preferences.instruments,
      fx: preferences.fx,
    },
    observedHoldings,
    limitations,
  };
}
