import { convertMinor, currencyExponent } from "../wealth/money.ts";
import type { FxRate } from "./deploy.ts";

function rateFor(fx: readonly FxRate[], base: string, quote: string): string | null {
  return fx.find((item) => item.baseCurrency === base && item.quoteCurrency === quote)?.rate ?? null;
}

export function toReportingMinor(
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
