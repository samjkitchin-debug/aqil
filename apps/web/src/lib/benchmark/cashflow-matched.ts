import { convertMinor, currencyExponent } from "../wealth/money.ts";

const UNIT_SCALE = 100_000_000n;

/** Signed external flow. Positive is a contribution. Negative is a withdrawal. */
export type ExternalCashflow = {
  cashflowId: string;
  occurredOn: string;
  amountMinor: bigint;
  currency: string;
};

/** Caller-supplied total-return level in major units. This module never fills a gap. */
export type BenchmarkLevel = {
  occurredOn: string;
  level: string;
  currency: string;
};

export type DatedFxRate = {
  occurredOn: string;
  baseCurrency: string;
  quoteCurrency: string;
  /** Quote-currency units per 1 base-currency unit. */
  rate: string;
};

export type FxAssumptions = {
  rates: readonly DatedFxRate[];
};

export type CostAssumptions = {
  /** Basis points removed from a contribution after conversion into the benchmark currency. */
  entryCostBps: string;
  /** Basis points added to the units sold so the net matches the withdrawal. */
  exitCostBps: string;
};

export type CashflowMatchedInput = {
  cashflows: readonly ExternalCashflow[] | undefined;
  benchmarkSeries: readonly BenchmarkLevel[] | undefined;
  fx: FxAssumptions | undefined;
  costs: CostAssumptions | undefined;
  valuationDate: string | undefined;
  reportingCurrency: string | undefined;
  /** Already in reporting-currency minor units. Not converted again. */
  portfolioEndingValueMinor: bigint | undefined;
};

export type MatchedLeg = {
  cashflowId: string;
  occurredOn: string;
  benchmarkDate: string;
  /** Null when the cashflow currency is already the benchmark currency. */
  fxDate: string | null;
  amountMinor: bigint;
  benchmarkCurrencyAmountMinor: bigint;
  costBps: string;
  unitsDelta: string;
};

export type CashflowMatchedComparison =
  | { status: "unavailable"; reason: string }
  | {
      status: "available";
      execution: "same-day";
      valuationDate: string;
      reportingCurrency: string;
      benchmarkCurrency: string;
      costs: CostAssumptions;
      assumptions: readonly string[];
      legs: readonly MatchedLeg[];
      passiveUnits: string;
      benchmarkLevelOnValuationDate: string;
      passiveEndingValueMinor: bigint;
      portfolioEndingValueMinor: bigint;
      /** Portfolio ending value minus passive ending value. Not a rate of return. */
      valueDifferenceMinor: bigint;
    };

type Decimal = { value: bigint; scale: bigint };

/**
 * Cashflow-matched passive comparison (AQ-026).
 * Same external flows and dates as the portfolio. A missing series, rate or cost stays unavailable.
 */
export function compareCashflowMatchedPassive(input: CashflowMatchedInput): CashflowMatchedComparison {
  if (!Array.isArray(input.benchmarkSeries)) {
    return unavailable("Benchmark series was not supplied.");
  }
  if (input.fx === undefined) {
    return unavailable("Foreign-exchange assumptions were not supplied.");
  }
  if (!Array.isArray(input.fx.rates)) {
    return unavailable("Foreign-exchange rates were not supplied.");
  }
  if (input.costs === undefined) {
    return unavailable("Cost assumptions were not supplied.");
  }
  if (input.costs.entryCostBps === undefined || input.costs.entryCostBps.trim() === "") {
    return unavailable("Entry cost was not supplied.");
  }
  if (input.costs.exitCostBps === undefined || input.costs.exitCostBps.trim() === "") {
    return unavailable("Exit cost was not supplied.");
  }
  if (!Array.isArray(input.cashflows)) {
    return unavailable("External cashflows were not supplied.");
  }
  if (input.valuationDate === undefined || input.valuationDate === "") {
    return unavailable("Valuation date was not supplied.");
  }
  if (!isIsoDate(input.valuationDate)) {
    return unavailable("Valuation date is invalid.");
  }
  if (input.reportingCurrency === undefined || input.reportingCurrency === "") {
    return unavailable("Reporting currency was not supplied.");
  }
  if (typeof input.portfolioEndingValueMinor !== "bigint") {
    return unavailable("Portfolio ending value was not supplied.");
  }

  const entryCost = parseBps(input.costs.entryCostBps);
  if (entryCost === null) return unavailable("Entry cost is invalid.");
  const exitCost = parseBps(input.costs.exitCostBps);
  if (exitCost === null) return unavailable("Exit cost is invalid.");

  if (input.benchmarkSeries.length === 0) {
    return unavailable("Benchmark series is empty.");
  }
  const benchmarkCurrency = input.benchmarkSeries[0]?.currency;
  if (benchmarkCurrency === undefined || !supportedCurrency(benchmarkCurrency)) {
    return unavailable("Benchmark currency is unsupported.");
  }
  if (input.benchmarkSeries.some((level) => level.currency !== benchmarkCurrency)) {
    return unavailable("Benchmark currencies differ across the series.");
  }
  if (!supportedCurrency(input.reportingCurrency)) {
    return unavailable("Reporting currency is unsupported.");
  }

  const seenIds = new Set<string>();
  for (const cashflow of input.cashflows) {
    if (cashflow.cashflowId.trim() === "") return unavailable("Cashflow id is missing.");
    if (seenIds.has(cashflow.cashflowId)) {
      return unavailable(`Cashflow id is duplicated: ${cashflow.cashflowId}.`);
    }
    seenIds.add(cashflow.cashflowId);
    if (!isIsoDate(cashflow.occurredOn)) return unavailable("Cashflow date is invalid.");
    if (cashflow.occurredOn > input.valuationDate) {
      return unavailable(`Cashflow date is after the valuation date: ${cashflow.cashflowId}.`);
    }
    if (!supportedCurrency(cashflow.currency)) {
      return unavailable(`Cashflow currency is unsupported: ${cashflow.cashflowId}.`);
    }
  }

  const ordered = [...input.cashflows].sort((left, right) => {
    const byDate = left.occurredOn.localeCompare(right.occurredOn);
    if (byDate !== 0) return byDate;
    const byDirection = Number(left.amountMinor < 0n) - Number(right.amountMinor < 0n);
    if (byDirection !== 0) return byDirection;
    return left.cashflowId.localeCompare(right.cashflowId);
  });

  let unitsScaled = 0n;
  const legs: MatchedLeg[] = [];
  for (const cashflow of ordered) {
    const level = findLevel(input.benchmarkSeries, cashflow.occurredOn, benchmarkCurrency);
    if (level.status === "unavailable") return level;
    const converted = convertToBenchmark(
      cashflow.amountMinor,
      cashflow.currency,
      benchmarkCurrency,
      cashflow.occurredOn,
      input.fx.rates,
      "cashflow",
    );
    if (converted.status === "unavailable") return converted;

    const magnitude = converted.amountMinor < 0n ? -converted.amountMinor : converted.amountMinor;
    if (cashflow.amountMinor >= 0n) {
      const investable = applyEntryCost(magnitude, entryCost);
      const bought = unitsForAmount(investable, level.parsed, benchmarkCurrency);
      if (bought.status === "unavailable") return bought;
      unitsScaled += bought.unitsScaled;
      legs.push({
        cashflowId: cashflow.cashflowId,
        occurredOn: cashflow.occurredOn,
        benchmarkDate: level.occurredOn,
        fxDate: converted.fxDate,
        amountMinor: cashflow.amountMinor,
        benchmarkCurrencyAmountMinor: converted.amountMinor,
        costBps: input.costs.entryCostBps,
        unitsDelta: formatUnits(bought.unitsScaled),
      });
      continue;
    }

    const gross = grossForExit(magnitude, exitCost);
    if (gross.status === "unavailable") return gross;
    const sold = unitsForAmount(gross.amountMinor, level.parsed, benchmarkCurrency);
    if (sold.status === "unavailable") return sold;
    if (sold.unitsScaled > unitsScaled) {
      return unavailable(`Withdrawal exceeds passive units on ${cashflow.occurredOn}.`);
    }
    unitsScaled -= sold.unitsScaled;
    legs.push({
      cashflowId: cashflow.cashflowId,
      occurredOn: cashflow.occurredOn,
      benchmarkDate: level.occurredOn,
      fxDate: converted.fxDate,
      amountMinor: cashflow.amountMinor,
      benchmarkCurrencyAmountMinor: converted.amountMinor,
      costBps: input.costs.exitCostBps,
      unitsDelta: formatUnits(-sold.unitsScaled),
    });
  }

  const endingLevel = findLevel(input.benchmarkSeries, input.valuationDate, benchmarkCurrency);
  if (endingLevel.status === "unavailable") return endingLevel;
  const endingBenchmarkMinor = amountForUnits(unitsScaled, endingLevel.parsed, benchmarkCurrency);
  if (endingBenchmarkMinor.status === "unavailable") return endingBenchmarkMinor;
  const reported = convertToBenchmark(
    endingBenchmarkMinor.amountMinor,
    benchmarkCurrency,
    input.reportingCurrency,
    input.valuationDate,
    input.fx.rates,
    "valuation",
  );
  if (reported.status === "unavailable") return reported;

  return {
    status: "available",
    execution: "same-day",
    valuationDate: input.valuationDate,
    reportingCurrency: input.reportingCurrency,
    benchmarkCurrency,
    costs: {
      entryCostBps: input.costs.entryCostBps,
      exitCostBps: input.costs.exitCostBps,
    },
    assumptions: [
      "Execution uses the benchmark level on the cashflow date. Levels are not interpolated.",
      "Foreign exchange uses a caller-supplied rate on that same date. Rates are not inverted or carried forward.",
      `Entry cost is ${input.costs.entryCostBps} basis points and exit cost is ${input.costs.exitCostBps} basis points, applied in the benchmark currency after conversion.`,
      "Contributions on a date are applied before withdrawals.",
      "Half-units round away from zero.",
    ],
    legs,
    passiveUnits: formatUnits(unitsScaled),
    benchmarkLevelOnValuationDate: endingLevel.level,
    passiveEndingValueMinor: reported.amountMinor,
    portfolioEndingValueMinor: input.portfolioEndingValueMinor,
    valueDifferenceMinor: input.portfolioEndingValueMinor - reported.amountMinor,
  };
}

function unavailable(reason: string): CashflowMatchedComparison {
  return { status: "unavailable", reason };
}

function isIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  if (year === undefined || month === undefined || day === undefined) return false;
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

function supportedCurrency(currency: string): boolean {
  if (!/^[A-Z]{3}$/.test(currency)) return false;
  try {
    currencyExponent(currency);
    return true;
  } catch {
    return false;
  }
}

function parseBps(text: string): Decimal | null {
  const trimmed = text.trim();
  if (!/^\d+(\.\d{1,4})?$/.test(trimmed)) return null;
  const parsed = parseDecimal(trimmed, true);
  if (parsed === null) return null;
  if (parsed.value >= 10_000n * parsed.scale) return null;
  return parsed;
}

function parseDecimal(text: string, allowZero: boolean): Decimal | null {
  if (!/^\d+(\.\d{1,10})?$/.test(text)) return null;
  const [whole, fraction = ""] = text.split(".");
  const scale = 10n ** BigInt(fraction.length);
  const value = BigInt(`${whole}${fraction || ""}`);
  if (value < 0n) return null;
  if (!allowZero && value === 0n) return null;
  return { value, scale };
}

function roundHalfAway(numerator: bigint, denominator: bigint): bigint {
  const negative = numerator < 0n;
  const absolute = negative ? -numerator : numerator;
  const quotient = absolute / denominator;
  const remainder = absolute % denominator;
  const rounded = remainder * 2n >= denominator ? quotient + 1n : quotient;
  return negative ? -rounded : rounded;
}

function applyEntryCost(amountMinor: bigint, cost: Decimal): bigint {
  const basis = 10_000n * cost.scale;
  return roundHalfAway(amountMinor * (basis - cost.value), basis);
}

function grossForExit(amountMinor: bigint, cost: Decimal): { status: "available"; amountMinor: bigint } | CashflowMatchedComparison {
  const basis = 10_000n * cost.scale;
  const keep = basis - cost.value;
  if (keep <= 0n) return unavailable("Exit cost is invalid.");
  return { status: "available", amountMinor: roundHalfAway(amountMinor * basis, keep) };
}

function findLevel(
  series: readonly BenchmarkLevel[],
  occurredOn: string,
  currency: string,
): { status: "available"; occurredOn: string; level: string; parsed: Decimal } | CashflowMatchedComparison {
  const sameCurrency = series.filter((level) => level.currency === currency);
  const onDate = sameCurrency.filter((level) => level.occurredOn === occurredOn);
  if (onDate.length > 1) return unavailable(`Benchmark level is ambiguous on ${occurredOn}.`);
  if (onDate.length === 0) {
    if (sameCurrency.length > 0) {
      return unavailable(`Benchmark level date does not match ${occurredOn}.`);
    }
    return unavailable(`Benchmark level is missing on ${occurredOn}.`);
  }
  const matched = onDate[0];
  if (matched === undefined || !isIsoDate(matched.occurredOn)) {
    return unavailable(`Benchmark level date is invalid on ${occurredOn}.`);
  }
  const parsed = parseDecimal(matched.level.trim(), false);
  if (parsed === null) return unavailable(`Benchmark level is invalid on ${occurredOn}.`);
  return { status: "available", occurredOn: matched.occurredOn, level: matched.level, parsed };
}

function convertToBenchmark(
  amountMinor: bigint,
  fromCurrency: string,
  toCurrency: string,
  occurredOn: string,
  rates: readonly DatedFxRate[],
  kind: "cashflow" | "valuation",
): { status: "available"; amountMinor: bigint; fxDate: string | null } | CashflowMatchedComparison {
  if (fromCurrency === toCurrency) {
    return { status: "available", amountMinor, fxDate: null };
  }
  const fromExponent = currencyExponent(fromCurrency);
  const toExponent = currencyExponent(toCurrency);
  if (fromExponent !== toExponent) {
    return unavailable(`Minor-unit scales differ between ${fromCurrency} and ${toCurrency}.`);
  }
  const pair = rates.filter((rate) => rate.baseCurrency === fromCurrency && rate.quoteCurrency === toCurrency);
  const onDate = pair.filter((rate) => rate.occurredOn === occurredOn);
  const when = kind === "valuation" ? "the valuation date" : "the cashflow date";
  if (onDate.length > 1) return unavailable(`Foreign-exchange rate is ambiguous on ${occurredOn}.`);
  if (onDate.length === 0) {
    if (pair.length > 0) {
      return unavailable(`Foreign-exchange rate date does not match ${when}.`);
    }
    return unavailable(`Foreign-exchange rate is missing on ${occurredOn} from ${fromCurrency} to ${toCurrency}.`);
  }
  const matched = onDate[0];
  if (matched === undefined) {
    return unavailable(`Foreign-exchange rate is missing on ${occurredOn} from ${fromCurrency} to ${toCurrency}.`);
  }
  let converted: bigint;
  try {
    converted = convertMinor(amountMinor, matched.rate.trim());
  } catch {
    return unavailable(`Foreign-exchange rate is invalid on ${occurredOn}.`);
  }
  return { status: "available", amountMinor: converted, fxDate: matched.occurredOn };
}

function unitsForAmount(
  amountMinor: bigint,
  level: Decimal,
  currency: string,
): { status: "available"; unitsScaled: bigint } | CashflowMatchedComparison {
  const exponent = currencyExponent(currency);
  const denominator = level.value * 10n ** BigInt(exponent);
  if (denominator <= 0n) return unavailable("Benchmark level is invalid.");
  const numerator = amountMinor * UNIT_SCALE * level.scale;
  return { status: "available", unitsScaled: roundHalfAway(numerator, denominator) };
}

function amountForUnits(
  unitsScaled: bigint,
  level: Decimal,
  currency: string,
): { status: "available"; amountMinor: bigint } | CashflowMatchedComparison {
  const exponent = currencyExponent(currency);
  const numerator = unitsScaled * level.value * 10n ** BigInt(exponent);
  const denominator = UNIT_SCALE * level.scale;
  if (denominator <= 0n) return unavailable("Benchmark level is invalid.");
  return { status: "available", amountMinor: roundHalfAway(numerator, denominator) };
}

function formatUnits(unitsScaled: bigint): string {
  const negative = unitsScaled < 0n;
  const absolute = negative ? -unitsScaled : unitsScaled;
  const whole = absolute / UNIT_SCALE;
  const fraction = (absolute % UNIT_SCALE).toString().padStart(8, "0");
  return `${negative ? "-" : ""}${whole.toString()}.${fraction}`;
}
