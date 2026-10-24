/**
 * Display formatting for stored indicator levels. The raw string is unchanged.
 * Rescaling runs only for units whose meaning is fixed by the source register.
 */

export type DisplayLevel = {
  /** Rounded figure for the panel headline. */
  headline: string;
  /** Precise figure for a plotted point. */
  precise: string;
  /** Value in the chart's display unit. */
  chartValue: number;
  /** Caption placed on the vertical axis. */
  axisUnit: string;
  /** Short suffix on axis ticks, such as "%". */
  tickSuffix: string;
  /** Unit placed beside an index headline. Rates and levels already include it. */
  beside: string | null;
  rescaled: boolean;
};

const PEOPLE = /^\d+$/;

export type CountNoun = "jobs" | "openings";

const COUNT_NOUN: Record<CountNoun, { one: string; many: string; million: string; axis: string }> = {
  jobs: { one: "job", many: "jobs", million: "million jobs", axis: "Million jobs" },
  openings: {
    one: "job opening",
    many: "job openings",
    million: "million job openings",
    axis: "Million job openings",
  },
};

export function displayLevel(raw: string, unit: string, countNoun?: CountNoun): DisplayLevel | null {
  const trimmed = raw.trim();
  if (!isDecimal(trimmed)) return null;
  if (unit === "percent" || unit === "percent_per_year" || unit === "percent_net_tightening") {
    return rateLevel(trimmed, unit);
  }
  if (unit === "thousands") return countLevel(trimmed, countNoun);
  if (unit === "usd_millions") return dollarLevel(trimmed);
  if (unit === "million yen, nominal, not a real volume index") return yenMillionLevel(trimmed);
  if (isIndexUnit(unit)) return indexLevel(trimmed, unit);
  const chartValue = Number(trimmed);
  if (!Number.isFinite(chartValue)) return null;
  return {
    headline: trimmed,
    precise: trimmed,
    chartValue,
    axisUnit: unitLabel(unit),
    tickSuffix: "",
    beside: null,
    rescaled: false,
  };
}

export function displayChange(diff: string, unit: string, countNoun?: CountNoun): string | null {
  const trimmed = diff.trim();
  if (!isDecimal(trimmed)) return null;
  if (isZero(trimmed)) return "Unchanged";
  if (unit === "percent" || unit === "percent_per_year" || unit === "percent_net_tightening") {
    return `${signed(rateMagnitude(trimmed))} percentage points`;
  }
  if (unit === "thousands") return countChange(trimmed, countNoun);
  if (unit === "usd_millions") {
    const money = dollarChange(trimmed);
    if (!money) return null;
    return money;
  }
  if (unit === "million yen, nominal, not a real volume index") {
    return `${signed(trimZeros(trimmed))} million yen`;
  }
  if (isIndexUnit(unit)) {
    const shown = decimalScale(trimmed) <= 3 ? trimZeros(trimmed) : showDecimals(trimmed, 2);
    return `${signed(shown)} index points`;
  }
  return `${signed(trimZeros(trimmed))} ${unitLabel(unit)}`;
}

export function unitLabel(unit: string): string {
  switch (unit) {
    case "percent":
      return "Percent";
    case "percent_per_year":
      return "Percent per year";
    case "percent_net_tightening":
      return "Net tightening";
    case "thousands":
      return "Thousands";
    case "usd_millions":
      return "US dollars";
    case "index_2017_100":
      return "Index (2017 = 100)";
    case "1982-84=100":
      return "Index (1982–84 = 100)";
    case "index, 2015 = 100":
      return "Index (2015 = 100)";
    case "index, 2021 = 100":
      return "Index (2021 = 100)";
    case "index, 2020 = 100":
      return "Index (2020 = 100)";
    case "index, 2025 = 100, three-decimal reference price index, not a nominal yen amount and not a real volume":
      return "Reference index (2025 = 100)";
    case "million yen, nominal, not a real volume index":
      return "Million yen";
    case "Index, amplitude adjusted":
      return "Index (amplitude adjusted)";
    case "US dollar, millions":
      return "Millions of US dollars";
    default:
      return unit;
  }
}

export function storedUnitPhrase(unit: string): string {
  switch (unit) {
    case "percent":
      return "percent";
    case "thousands":
      return "thousands";
    case "usd_millions":
      return "millions of US dollars";
    case "percent_per_year":
      return "percent per year";
    case "percent_net_tightening":
      return "percent net tightening";
    case "index_2017_100":
      return "index, 2017 = 100";
    case "index, 2021 = 100":
      return "index, 2021 = 100";
    case "index, 2020 = 100":
      return "index, 2020 = 100";
    case "1982-84=100":
      return "1982–84 = 100";
    default:
      return unit;
  }
}

function rateLevel(raw: string, unit: string): DisplayLevel | null {
  const shown = showDecimals(raw, Math.min(2, Math.max(1, decimalScale(raw))));
  const chartValue = Number(raw);
  if (!Number.isFinite(chartValue)) return null;
  const headline =
    unit === "percent_per_year"
      ? `${shown}% per year`
      : unit === "percent_net_tightening"
        ? `${shown}% net tightening`
        : `${shown}%`;
  return {
    headline,
    precise: headline,
    chartValue,
    axisUnit: unitLabel(unit),
    tickSuffix: "%",
    beside: null,
    rescaled: false,
  };
}

function countLevel(raw: string, countNoun: CountNoun | undefined): DisplayLevel | null {
  const labels = countNoun ? COUNT_NOUN[countNoun] : null;
  if (!labels) {
    const chartValue = Number(raw);
    if (!Number.isFinite(chartValue)) return null;
    return {
      headline: raw,
      precise: raw,
      chartValue,
      axisUnit: "Thousands",
      tickSuffix: "",
      beside: null,
      rescaled: false,
    };
  }
  const millions = divideExact(raw, 1000n);
  if (!millions) return null;
  const chartValue = Number(millions);
  if (!Number.isFinite(chartValue)) return null;
  const magnitude = Math.abs(chartValue);
  const headlineDecimals = magnitude >= 20 ? 1 : 2;
  return {
    headline: `${showDecimals(millions, headlineDecimals)} ${labels.million}`,
    precise: `${trimZeros(showDecimals(millions, 3))} ${labels.million}`,
    chartValue,
    axisUnit: labels.axis,
    tickSuffix: "",
    beside: null,
    rescaled: true,
  };
}

function countChange(diff: string, countNoun: CountNoun | undefined): string | null {
  const labels = countNoun ? COUNT_NOUN[countNoun] : null;
  if (!labels) return `${signed(trimZeros(diff))} thousand`;
  const count = multiplyExact(diff, 1000n);
  if (!count) return null;
  const word = absolute(count) === "1" ? labels.one : labels.many;
  return `${signed(groupInteger(count))} ${word}`;
}

function dollarLevel(raw: string): DisplayLevel | null {
  const millions = Number(raw);
  if (!Number.isFinite(millions)) return null;
  const abs = Math.abs(millions);
  if (abs >= 1_000_000) {
    const trillions = divideExact(raw, 1_000_000n);
    if (!trillions) return null;
    return {
      headline: `${moneySign(trillions)}$${trimZeros(showDecimals(absolute(trillions), 2))} trillion`,
      precise: `${moneySign(trillions)}$${trimZeros(showDecimals(absolute(trillions), 3))} trillion`,
      chartValue: Number(trillions),
      axisUnit: "US$ trillion",
      tickSuffix: "",
      beside: null,
      rescaled: true,
    };
  }
  if (abs >= 1_000) {
    const billions = divideExact(raw, 1_000n);
    if (!billions) return null;
    return {
      headline: `${moneySign(billions)}$${trimZeros(showDecimals(absolute(billions), 2))} billion`,
      precise: `${moneySign(billions)}$${trimZeros(showDecimals(absolute(billions), 3))} billion`,
      chartValue: Number(billions),
      axisUnit: "US$ billion",
      tickSuffix: "",
      beside: null,
      rescaled: true,
    };
  }
  return {
    headline: `${moneySign(raw)}$${groupInteger(absolute(raw))} million`,
    precise: `${moneySign(raw)}$${trimZeros(raw)} million`,
    chartValue: millions,
    axisUnit: "US$ million",
    tickSuffix: "",
    beside: null,
    rescaled: true,
  };
}

function dollarChange(diff: string): string | null {
  const millions = Number(diff);
  if (!Number.isFinite(millions)) return null;
  const abs = Math.abs(millions);
  if (abs >= 1_000_000) {
    const trillions = divideExact(absolute(diff), 1_000_000n);
    if (!trillions) return null;
    return `${signedMoney(diff, showDecimals(trillions, 2), "trillion")}`;
  }
  if (abs >= 1_000) {
    const billions = divideExact(absolute(diff), 1_000n);
    if (!billions) return null;
    return `${signedMoney(diff, showDecimals(billions, 2), "billion")}`;
  }
  return `${signedMoney(diff, groupInteger(absolute(diff)), "million")}`;
}

function indexLevel(raw: string, unit: string): DisplayLevel | null {
  const scale = decimalScale(raw);
  const headlineDecimals = scale > 4 ? 1 : scale === 4 ? 2 : scale;
  const preciseDecimals = scale > 4 ? 2 : scale;
  const chartValue = Number(raw);
  if (!Number.isFinite(chartValue)) return null;
  return {
    headline: showDecimals(raw, Math.max(headlineDecimals, 0)),
    precise: showDecimals(raw, Math.max(preciseDecimals, 0)),
    chartValue,
    axisUnit: unitLabel(unit).replace(/^Index/, "Index points"),
    tickSuffix: "",
    beside: unitLabel(unit),
    rescaled: false,
  };
}

function isIndexUnit(unit: string): boolean {
  return (
    unit === "index_2017_100" ||
    unit === "1982-84=100" ||
    unit === "index, 2015 = 100" ||
    unit === "index, 2021 = 100" ||
    unit === "index, 2020 = 100" ||
    unit ===
      "index, 2025 = 100, three-decimal reference price index, not a nominal yen amount and not a real volume" ||
    unit === "Index, amplitude adjusted"
  );
}

function yenMillionLevel(raw: string): DisplayLevel | null {
  const chartValue = Number(raw);
  if (!Number.isFinite(chartValue)) return null;
  return {
    headline: trimZeros(raw),
    precise: trimZeros(raw),
    chartValue,
    axisUnit: "Million yen",
    tickSuffix: "",
    beside: "Million yen",
    rescaled: false,
  };
}

function signedMoney(diff: string, magnitude: string, scale: string): string {
  const sign = diff.startsWith("-") ? "-" : "+";
  return `${sign}$${trimZeros(magnitude)} ${scale}`;
}

function moneySign(raw: string): string {
  return raw.startsWith("-") ? "-" : "";
}

function rateMagnitude(raw: string): string {
  const shown = trimZeros(showDecimals(raw, 2));
  return shown.includes(".") ? shown : `${shown}.0`;
}

function signed(magnitude: string): string {
  return magnitude.startsWith("-") ? magnitude : `+${magnitude}`;
}

function absolute(raw: string): string {
  return raw.startsWith("-") ? raw.slice(1) : raw;
}

function isZero(raw: string): boolean {
  return /^-?0+(\.0+)?$/.test(raw);
}

function isDecimal(raw: string): boolean {
  return /^-?\d+(\.\d+)?$/.test(raw);
}

function decimalScale(raw: string): number {
  return absolute(raw).split(".")[1]?.length ?? 0;
}

export function showDecimals(raw: string, decimals: number): string {
  const negative = raw.startsWith("-");
  const body = absolute(raw);
  const [whole, frac = ""] = body.split(".");
  if (frac.length <= decimals) {
    if (decimals === 0) return negative ? `-${whole}` : whole;
    const padded = frac.padEnd(decimals, "0");
    return `${negative ? "-" : ""}${whole}.${padded}`;
  }
  const keep = frac.slice(0, decimals);
  const next = frac[decimals] ?? "0";
  // Half away from zero: a following digit of 5 or more rounds away.
  if (next < "5") {
    return decimals === 0
      ? `${negative ? "-" : ""}${whole}`
      : `${negative ? "-" : ""}${whole}.${keep}`;
  }
  const combined = `${whole}${keep}`.replace(/^0+(?=\d)/, "");
  const bumped = (BigInt(combined || "0") + 1n).toString().padStart(whole.length + decimals, "0");
  if (decimals === 0) return `${negative ? "-" : ""}${bumped}`;
  const nextWhole = bumped.slice(0, -decimals);
  const nextFrac = bumped.slice(-decimals);
  return `${negative ? "-" : ""}${nextWhole}.${nextFrac}`;
}

function trimZeros(raw: string): string {
  if (!raw.includes(".")) return raw;
  return raw.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
}

function groupInteger(raw: string): string {
  if (!PEOPLE.test(absolute(raw).split(".")[0] ?? "")) return raw;
  const negative = raw.startsWith("-");
  const whole = absolute(raw).split(".")[0] ?? "0";
  const grouped = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 }).format(Number(whole));
  return negative ? `-${grouped}` : grouped;
}

function toScaled(raw: string): { int: bigint; scale: number } | null {
  if (!isDecimal(raw)) return null;
  const negative = raw.startsWith("-");
  const body = absolute(raw);
  const [whole, frac = ""] = body.split(".");
  const digits = `${whole}${frac}`.replace(/^0+(?=\d)/, "");
  return { int: BigInt(digits || "0") * (negative ? -1n : 1n), scale: frac.length };
}

function divideExact(raw: string, divisor: bigint): string | null {
  const scaled = toScaled(raw);
  if (!scaled || divisor === 0n) return null;
  const negative = scaled.int < 0n;
  let remainder = negative ? -scaled.int : scaled.int;
  const denominator = divisor * 10n ** BigInt(scaled.scale);
  const whole = remainder / denominator;
  remainder %= denominator;
  let frac = "";
  for (let index = 0; index < 8 && remainder !== 0n; index += 1) {
    remainder *= 10n;
    frac += (remainder / denominator).toString();
    remainder %= denominator;
  }
  const body = frac ? `${whole.toString()}.${frac}` : whole.toString();
  return negative ? `-${body}` : body;
}

function multiplyExact(raw: string, factor: bigint): string | null {
  const scaled = toScaled(raw);
  if (!scaled) return null;
  const negative = scaled.int < 0n;
  const product = (negative ? -scaled.int : scaled.int) * factor;
  const text = product.toString().padStart(scaled.scale + 1, "0");
  if (scaled.scale === 0) return negative ? `-${text}` : text;
  const whole = text.slice(0, -scaled.scale);
  const frac = text.slice(-scaled.scale).replace(/0+$/, "");
  const body = frac ? `${whole}.${frac}` : whole;
  return negative ? `-${body}` : body;
}
