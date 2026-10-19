import {
  assertTargets,
  allocateExternalContribution,
  monetaryGaps,
  type InvestableClass,
  type Target,
} from "../wealth/allocation.ts";
import { convertMinor, currencyExponent } from "../wealth/money.ts";

export type ClassValue = {
  assetClass: InvestableClass;
  currency: string;
  amountMinor: bigint;
};

/** An instrument the caller has explicitly approved. An empty list is not a default universe. */
export type ApprovedInstrument = {
  id: string;
  name: string;
  assetClass: InvestableClass;
  currency: string;
  /** Smallest tradable multiple. One means whole units. */
  minimumUnit: bigint;
  priceMinor: bigint;
  /** Extra minor-unit cost per unit, in the instrument currency, when a verified cost exists. */
  costMinorPerUnit?: bigint;
};

export type FxRate = {
  baseCurrency: string;
  quoteCurrency: string;
  rate: string;
};

export type DeployCapitalInput = {
  reportingCurrency: string;
  classValues: readonly ClassValue[];
  targets: readonly Target[] | null;
  /** Null means no budget has been set. Zero is not a deployment. */
  additionalCashMinor: bigint | null;
  instruments: readonly ApprovedInstrument[] | null;
  fx: readonly FxRate[];
};

export type ExposureSide = "underweight" | "overweight" | "in line";

export type ClassExposure = {
  assetClass: InvestableClass;
  currentMinor: bigint;
  currentWeightBps: number;
  targetWeightBps: number;
  gapMinor: bigint;
  side: ExposureSide;
  deploymentMinor: bigint;
};

export type InstrumentDeployment = {
  id: string;
  name: string;
  assetClass: InvestableClass;
  currency: string;
  status: "planned" | "unavailable";
  reason: string | null;
  units: bigint | null;
  spendMinor: bigint | null;
};

export type DeployCapitalResult = {
  reportingCurrency: string;
  missing: string[];
  exposures: ClassExposure[];
  instruments: InstrumentDeployment[];
  /** Reporting-currency minor units left after whole-unit purchases. */
  unallocatedMinor: bigint | null;
};

const CLASS_ORDER: readonly InvestableClass[] = [
  "global_equity",
  "thematic_technology",
  "investment_grade_bonds",
  "cash_investable",
];

function targetsReady(targets: readonly Target[] | null): targets is readonly Target[] {
  if (!targets || targets.length === 0) return false;
  try {
    assertTargets(targets);
    return true;
  } catch {
    return false;
  }
}

function rateFor(fx: readonly FxRate[], base: string, quote: string): string | null {
  return fx.find((item) => item.baseCurrency === base && item.quoteCurrency === quote)?.rate ?? null;
}

function toReporting(
  amountMinor: bigint,
  currency: string,
  reportingCurrency: string,
  fx: readonly FxRate[],
): { ok: true; amountMinor: bigint } | { ok: false; reason: string } {
  if (currency === reportingCurrency) return { ok: true, amountMinor };
  let sourceExponent: number;
  let reportingExponent: number;
  try {
    sourceExponent = currencyExponent(currency);
    reportingExponent = currencyExponent(reportingCurrency);
  } catch {
    return { ok: false, reason: `fx ${currency} to ${reportingCurrency}` };
  }
  if (sourceExponent !== reportingExponent) {
    return { ok: false, reason: `fx ${currency} to ${reportingCurrency}` };
  }
  const rate = rateFor(fx, currency, reportingCurrency);
  if (!rate) return { ok: false, reason: `fx ${currency} to ${reportingCurrency}` };
  try {
    return { ok: true, amountMinor: convertMinor(amountMinor, rate) };
  } catch {
    return { ok: false, reason: `fx ${currency} to ${reportingCurrency}` };
  }
}

function weightBps(amounts: readonly bigint[]): number[] {
  const total = amounts.reduce((sum, amount) => sum + amount, BigInt(0));
  if (total === BigInt(0)) return amounts.map(() => 0);
  const weights = amounts.map((amount) => Number((amount * BigInt(10000)) / total));
  let drift = 10000 - weights.reduce((sum, weight) => sum + weight, 0);
  if (drift !== 0) {
    let index = 0;
    for (let i = 1; i < amounts.length; i += 1) {
      if (amounts[i] > amounts[index]) index = i;
    }
    weights[index] += drift;
  }
  return weights;
}

function sideFor(gapMinor: bigint): ExposureSide {
  if (gapMinor > BigInt(0)) return "underweight";
  if (gapMinor < BigInt(0)) return "overweight";
  return "in line";
}

function deployInstruments(
  deployment: readonly { assetClass: InvestableClass; amountMinor: bigint }[],
  instruments: readonly ApprovedInstrument[],
  reportingCurrency: string,
  fx: readonly FxRate[],
): { lines: InstrumentDeployment[]; unallocatedMinor: bigint } {
  const lines: InstrumentDeployment[] = [];
  let unallocated = BigInt(0);
  for (const slice of deployment) {
    if (slice.amountMinor <= BigInt(0)) continue;
    const choices = instruments.filter((instrument) => instrument.assetClass === slice.assetClass);
    let remaining = slice.amountMinor;
    if (choices.length === 0) {
      unallocated += remaining;
      continue;
    }
    for (const instrument of choices) {
      const price = toReporting(instrument.priceMinor, instrument.currency, reportingCurrency, fx);
      const costAmount = instrument.costMinorPerUnit ?? BigInt(0);
      const cost = toReporting(costAmount, instrument.currency, reportingCurrency, fx);
      if (!price.ok || !cost.ok || instrument.minimumUnit <= BigInt(0) || instrument.priceMinor <= BigInt(0)) {
        lines.push({
          id: instrument.id,
          name: instrument.name,
          assetClass: instrument.assetClass,
          currency: instrument.currency,
          status: "unavailable",
          reason: price.ok ? (cost.ok ? "trading unit or price is not usable" : cost.reason) : price.reason,
          units: null,
          spendMinor: null,
        });
        continue;
      }
      const unitCost = price.amountMinor + cost.amountMinor;
      if (unitCost <= BigInt(0) || remaining < unitCost * instrument.minimumUnit) continue;
      const affordable = remaining / unitCost;
      const units = (affordable / instrument.minimumUnit) * instrument.minimumUnit;
      if (units <= BigInt(0)) continue;
      const spend = units * unitCost;
      remaining -= spend;
      lines.push({
        id: instrument.id,
        name: instrument.name,
        assetClass: instrument.assetClass,
        currency: instrument.currency,
        status: "planned",
        reason: null,
        units,
        spendMinor: spend,
      });
    }
    unallocated += remaining;
  }
  return { lines, unallocatedMinor: unallocated };
}

/**
 * Read-only deployment of additional cash toward explicit targets.
 * No order is created. Missing targets, budget, universe or FX stay visible.
 */
export function deployCapital(input: DeployCapitalInput): DeployCapitalResult {
  const missing: string[] = [];
  const readyTargets = targetsReady(input.targets);
  if (!readyTargets) missing.push("allocation targets");
  if (input.additionalCashMinor === null || input.additionalCashMinor <= BigInt(0)) {
    missing.push("investment budget");
  }
  if (!input.instruments || input.instruments.length === 0) missing.push("approved instruments");

  const reporting = new Map<InvestableClass, bigint>();
  for (const row of input.classValues) {
    const converted = toReporting(row.amountMinor, row.currency, input.reportingCurrency, input.fx);
    if (!converted.ok) {
      if (!missing.includes(converted.reason)) missing.push(converted.reason);
      continue;
    }
    reporting.set(row.assetClass, (reporting.get(row.assetClass) ?? BigInt(0)) + converted.amountMinor);
  }

  const targets = input.targets;
  if (!targets || !readyTargets || missing.some((item) => item.startsWith("fx "))) {
    return {
      reportingCurrency: input.reportingCurrency,
      missing,
      exposures: [],
      instruments: [],
      unallocatedMinor: null,
    };
  }

  const classValues = CLASS_ORDER.filter(
    (assetClass) => targets.some((target) => target.assetClass === assetClass) || reporting.has(assetClass),
  ).map((assetClass) => ({
    assetClass,
    currentMinor: reporting.get(assetClass) ?? BigInt(0),
  }));
  const gaps = monetaryGaps(classValues, targets, BigInt(0));
  const weights = weightBps(classValues.map((row) => row.currentMinor));
  const budget =
    input.additionalCashMinor !== null && input.additionalCashMinor > BigInt(0) ? input.additionalCashMinor : null;
  const allocated = budget ? allocateExternalContribution(classValues, targets, budget) : [];
  const deploymentByClass = new Map(allocated.map((row) => [row.assetClass, row.amountMinor]));

  const exposures: ClassExposure[] = classValues.map((row, index) => {
    const target = targets.find((item) => item.assetClass === row.assetClass);
    const gap = gaps.find((item) => item.assetClass === row.assetClass);
    const gapMinor = gap?.gapMinor ?? BigInt(0);
    return {
      assetClass: row.assetClass,
      currentMinor: row.currentMinor,
      currentWeightBps: weights[index] ?? 0,
      targetWeightBps: target?.targetWeightBps ?? 0,
      gapMinor,
      side: sideFor(gapMinor),
      deploymentMinor: deploymentByClass.get(row.assetClass) ?? BigInt(0),
    };
  });

  if (!budget || !input.instruments || input.instruments.length === 0) {
    return {
      reportingCurrency: input.reportingCurrency,
      missing,
      exposures,
      instruments: [],
      unallocatedMinor: null,
    };
  }

  const deployed = deployInstruments(allocated, input.instruments, input.reportingCurrency, input.fx);
  return {
    reportingCurrency: input.reportingCurrency,
    missing,
    exposures,
    instruments: deployed.lines,
    unallocatedMinor: deployed.unallocatedMinor,
  };
}
