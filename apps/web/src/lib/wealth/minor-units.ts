/** Currency amounts in minor units (e.g. cents). All portfolio maths uses bigint. */

export function minorFromDecimal(amount: string): bigint {
  const trimmed = amount.trim();
  if (!/^-?\d+(\.\d{1,2})?$/.test(trimmed)) {
    throw new Error("invalid decimal amount");
  }
  const negative = trimmed.startsWith("-");
  const normalised = negative ? trimmed.slice(1) : trimmed;
  const [whole, frac = ""] = normalised.split(".");
  const padded = (frac + "00").slice(0, 2);
  const minor = BigInt(whole) * 100n + BigInt(padded);
  return negative ? -minor : minor;
}

export function formatMinor(minor: bigint, currency: string): string {
  const negative = minor < 0n;
  const abs = negative ? -minor : minor;
  const whole = abs / 100n;
  const cents = abs % 100n;
  const body = `${whole}.${cents.toString().padStart(2, "0")}`;
  return negative ? `-${body} ${currency}` : `${body} ${currency}`;
}

export function sumMinor(values: readonly bigint[]): bigint {
  return values.reduce((acc, value) => acc + value, 0n);
}

/** Allocate totalMinor across weights (bps) with exact reconciliation (largest remainder). */
export function allocateByWeightsBps(
  totalMinor: bigint,
  weightsBps: readonly { key: string; bps: number }[],
): Map<string, bigint> {
  if (totalMinor < 0n) {
    throw new Error("total must be non-negative");
  }
  const totalBps = weightsBps.reduce((acc, row) => acc + row.bps, 0);
  if (totalBps <= 0) {
    throw new Error("weights must sum to a positive bps total");
  }
  const shares: { key: string; floor: bigint; remainder: bigint }[] = [];
  let allocated = 0n;
  for (const row of weightsBps) {
    const product = totalMinor * BigInt(row.bps);
    const floor = product / BigInt(totalBps);
    const remainder = product % BigInt(totalBps);
    shares.push({ key: row.key, floor, remainder });
    allocated += floor;
  }
  let left = totalMinor - allocated;
  const sorted = [...shares].sort((a, b) => {
    if (a.remainder === b.remainder) {
      return a.key.localeCompare(b.key);
    }
    return a.remainder > b.remainder ? -1 : 1;
  });
  const result = new Map<string, bigint>();
  for (const row of shares) {
    result.set(row.key, row.floor);
  }
  for (const row of sorted) {
    if (left <= 0n) break;
    result.set(row.key, (result.get(row.key) ?? 0n) + 1n);
    left -= 1n;
  }
  const check = sumMinor([...result.values()]);
  if (check !== totalMinor) {
    throw new Error("allocation reconciliation failed");
  }
  return result;
}
