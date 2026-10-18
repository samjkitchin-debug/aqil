const EXPONENT: Record<string, number> = {
  SGD: 2,
  USD: 2,
  AUD: 2,
  EUR: 2,
  GBP: 2,
  JPY: 0,
};

export function currencyExponent(currency: string): number {
  const exponent = EXPONENT[currency];
  if (exponent === undefined) {
    throw new Error(`unsupported currency ${currency}`);
  }
  return exponent;
}

/** Parse a major-unit amount into minor units. Extra fraction digits are rejected. */
export function parseMajorToMinor(major: string, currency: string): bigint {
  const exponent = currencyExponent(currency);
  const trimmed = major.trim();
  if (!/^\d+(\.\d+)?$/.test(trimmed)) {
    throw new Error("invalid amount");
  }
  const [whole, fraction = ""] = trimmed.split(".");
  if (fraction.length > exponent) {
    throw new Error("too many decimal places");
  }
  const scale = BigInt(10) ** BigInt(exponent);
  const padded = fraction.padEnd(exponent, "0");
  return BigInt(whole) * scale + BigInt(padded || "0");
}

export function formatMinor(amountMinor: bigint, currency: string): string {
  const exponent = currencyExponent(currency);
  const scale = BigInt(10) ** BigInt(exponent);
  const negative = amountMinor < BigInt(0);
  const absolute = negative ? -amountMinor : amountMinor;
  const whole = absolute / scale;
  if (exponent === 0) {
    return `${negative ? "-" : ""}${currency} ${whole.toString()}`;
  }
  const fraction = (absolute % scale).toString().padStart(exponent, "0");
  return `${negative ? "-" : ""}${currency} ${whole.toString()}.${fraction}`;
}

/**
 * Convert minor units by a quote-per-base rate.
 * Both currencies must use the same number of minor digits.
 * Half rounds away from zero. A missing rate is never treated as 1.
 */
export function convertMinor(amountMinor: bigint, rate: string): bigint {
  if (!/^\d+(\.\d{1,10})?$/.test(rate)) {
    throw new Error("invalid fx rate");
  }
  const [whole, fraction = ""] = rate.split(".");
  const scale = BigInt(10) ** BigInt(fraction.length);
  const scaled = BigInt(`${whole}${fraction}`);
  if (scaled <= BigInt(0)) {
    throw new Error("invalid fx rate");
  }
  if (scale === BigInt(1)) return amountMinor * scaled;
  const product = amountMinor * scaled;
  const half = scale / BigInt(2);
  const sign = product < BigInt(0) ? -BigInt(1) : BigInt(1);
  return ((product * sign) + half) / scale * sign;
}
