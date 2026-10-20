import { convertMinor, currencyExponent } from "./money.ts";
import { replayJournal, type FxRate, type JournalEvent, type JournalReplay, type MoneyStatus, type PriceQuote } from "./journal.ts";

export type SuppliedPrice = {
  instrumentId: string;
  currency: string;
  unitPriceMinor: bigint;
  asOf: string;
  source: "supplied";
};

export type SuppliedRate = {
  baseCurrency: string;
  quoteCurrency: string;
  rate: string;
  asOf: string;
  source: "supplied";
};

export type MarketValueView =
  | {
      status: "available";
      currency: string;
      amountMinor: bigint;
      asOf: string;
      source: "supplied" | "no holding";
    }
  | { status: "unavailable"; asOf: string; reason: string };

export function addSuppliedPrice(prices: readonly SuppliedPrice[], price: SuppliedPrice): SuppliedPrice[] {
  const key = priceKey(price);
  const existing = prices.find((item) => priceKey(item) === key);
  if (existing) {
    if (existing.unitPriceMinor !== price.unitPriceMinor) throw new Error("conflict");
    return [...prices];
  }
  return [...prices, price];
}

export function addSuppliedRate(rates: readonly SuppliedRate[], rate: SuppliedRate): SuppliedRate[] {
  if (rate.baseCurrency === rate.quoteCurrency) throw new Error("invalid rate");
  if (currencyExponent(rate.baseCurrency) !== currencyExponent(rate.quoteCurrency)) {
    throw new Error("invalid rate");
  }
  if (!/^\d+(\.\d{1,10})?$/.test(rate.rate) || /^0+(?:\.0+)?$/.test(rate.rate)) throw new Error("invalid rate");
  const key = rateKey(rate);
  const existing = rates.find((item) => rateKey(item) === key);
  if (existing) {
    if (existing.rate !== rate.rate) throw new Error("conflict");
    return [...rates];
  }
  return [...rates, rate];
}

export function quotesOn(prices: readonly SuppliedPrice[], asOf: string): PriceQuote[] {
  return prices
    .filter((price) => price.asOf === asOf)
    .map((price) => ({
      instrumentId: price.instrumentId,
      currency: price.currency,
      unitPriceMinor: price.unitPriceMinor,
    }));
}

export function ratesOn(rates: readonly SuppliedRate[], asOf: string, reportingCurrency: string): FxRate[] {
  return rates
    .filter((rate) => rate.asOf === asOf && rate.quoteCurrency === reportingCurrency)
    .filter((rate) => sameExponent(rate.baseCurrency, reportingCurrency))
    .map((rate) => ({
      baseCurrency: rate.baseCurrency,
      quoteCurrency: rate.quoteCurrency,
      rate: rate.rate,
    }));
}

export function replayAtDate(
  events: readonly JournalEvent[],
  prices: readonly SuppliedPrice[],
  rates: readonly SuppliedRate[],
  reportingCurrency: string,
  asOf: string,
): JournalReplay {
  const visible = events.filter((event) => event.occurredOn <= asOf);
  return replayJournal(visible, reportingCurrency, ratesOn(rates, asOf, reportingCurrency), quotesOn(prices, asOf));
}

export function explainMarketValue(
  events: readonly JournalEvent[],
  prices: readonly SuppliedPrice[],
  rates: readonly SuppliedRate[],
  reportingCurrency: string,
  asOf: string,
): { replay: JournalReplay; market: MarketValueView } {
  const replay = replayAtDate(events, prices, rates, reportingCurrency, asOf);
  if (replay.positions.length === 0) {
    return {
      replay,
      market: {
        status: "available",
        currency: reportingCurrency,
        amountMinor: 0n,
        asOf,
        source: "no holding",
      },
    };
  }
  if (replay.marketValue.status === "available") {
    return {
      replay,
      market: {
        status: "available",
        currency: replay.marketValue.currency,
        amountMinor: replay.marketValue.amountMinor,
        asOf,
        source: "supplied",
      },
    };
  }
  const quotes = quotesOn(prices, asOf);
  const fx = ratesOn(rates, asOf, reportingCurrency);
  for (const position of replay.positions) {
    const quote = quotes.find(
      (price) => price.instrumentId === position.instrumentId && price.currency === position.currency,
    );
    if (!quote) {
      const otherCurrency = prices.find(
        (price) =>
          price.instrumentId === position.instrumentId &&
          price.asOf === asOf &&
          price.currency !== position.currency,
      );
      if (otherCurrency) {
        return {
          replay,
          market: {
            status: "unavailable",
            asOf,
            reason: `The supplied price for ${position.instrumentId} is in ${otherCurrency.currency}, which does not match the holding currency ${position.currency}.`,
          },
        };
      }
      return {
        replay,
        market: {
          status: "unavailable",
          asOf,
          reason: `No price was supplied for ${position.instrumentId} as of ${asOf}.`,
        },
      };
    }
    if (position.currency !== reportingCurrency) {
      const supplied = rates.some(
        (rate) =>
          rate.asOf === asOf &&
          rate.baseCurrency === position.currency &&
          rate.quoteCurrency === reportingCurrency,
      );
      if (supplied && !sameExponent(position.currency, reportingCurrency)) {
        return {
          replay,
          market: { status: "unavailable", asOf, reason: "Currency conversion is unavailable." },
        };
      }
      if (!fx.some((rate) => rate.baseCurrency === position.currency)) {
        return {
          replay,
          market: {
            status: "unavailable",
            asOf,
            reason: `No exchange rate was supplied from ${position.currency} to ${reportingCurrency} as of ${asOf}.`,
          },
        };
      }
    }
  }
  return {
    replay,
    market: { status: "unavailable", asOf, reason: "Investment value is unavailable for this date." },
  };
}

export function unrealisedGain(
  replay: JournalReplay,
  rates: readonly FxRate[],
  reportingCurrency: string,
): MoneyStatus {
  if (replay.positions.length === 0) {
    return { status: "available", currency: reportingCurrency, amountMinor: 0n };
  }
  if (replay.marketValue.status !== "available") return { status: "unavailable" };
  let cost = 0n;
  for (const position of replay.positions) {
    if (position.costMinor === null) return { status: "unavailable" };
    const converted = toReporting(position.costMinor, position.currency, reportingCurrency, rates);
    if (converted === null) return { status: "unavailable" };
    cost += converted;
  }
  return {
    status: "available",
    currency: reportingCurrency,
    amountMinor: replay.marketValue.amountMinor - cost,
  };
}

export function toReporting(
  amount: bigint,
  currency: string,
  reportingCurrency: string,
  rates: readonly FxRate[],
): bigint | null {
  if (currency === reportingCurrency) return amount;
  if (!sameExponent(currency, reportingCurrency)) return null;
  const rate = rates.find((item) => item.baseCurrency === currency && item.quoteCurrency === reportingCurrency);
  if (!rate) return null;
  return convertMinor(amount, rate.rate);
}

function sameExponent(left: string, right: string): boolean {
  try {
    return currencyExponent(left) === currencyExponent(right);
  } catch {
    return false;
  }
}

function priceKey(price: SuppliedPrice): string {
  return `${price.instrumentId}\u0000${price.currency}\u0000${price.asOf}`;
}

function rateKey(rate: SuppliedRate): string {
  return `${rate.baseCurrency}\u0000${rate.quoteCurrency}\u0000${rate.asOf}`;
}
