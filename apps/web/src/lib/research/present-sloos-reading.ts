/** Plain-language presentation of one stored SLOOS reading. */

export type SloosReadingView = {
  narrative: string;
  sharePercent: string;
  observationPeriod: string;
  directionLabel: string;
  interpretation: string;
  limitations: string[];
  previousPeriod: string | null;
  previousSharePercent: string | null;
  sourceId: string;
  datasetId: string;
  methodId: string;
  methodVersion: string;
  runId: string;
  payloadHash: string;
  observationId: string;
  retrievedAt: string;
  analysisMode: string;
};

const DIRECTION_LABELS: Record<string, string> = {
  net_tightening: "net tightening",
  net_easing: "net easing",
  balanced_net_tightening_and_easing: "a balance of tightening and easing",
};

export function directionPhrase(label: string): string {
  return DIRECTION_LABELS[label] ?? label;
}

export function quarterStartingLabel(isoDate: string): string {
  const [year, month, day] = isoDate.slice(0, 10).split("-");
  if (!year || !month || !day) return isoDate;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function whyItMatters(directionLabel: string, interpretation: string): string {
  const meaning: Record<string, string> = {
    net_tightening:
      "A positive share means more domestic banks reported tightening standards on commercial and industrial loans to large and middle-market firms than reported easing them.",
    net_easing:
      "A negative share means more domestic banks reported easing standards on commercial and industrial loans to large and middle-market firms than reported tightening them.",
    balanced_net_tightening_and_easing:
      "A zero share means the share of domestic banks reporting tighter standards on commercial and industrial loans to large and middle-market firms equals the share reporting easier standards. It does not mean every bank left standards unchanged.",
  };
  const lead = meaning[directionLabel] ?? "The stored share is a survey balance of reported tightening and easing.";
  return `${lead} ${interpretation}`.trim();
}

export function shareDifferenceTenths(current: string, previous: string): number | null {
  const currentTenths = _tenths(current);
  const previousTenths = _tenths(previous);
  if (currentTenths === null || previousTenths === null) return null;
  return currentTenths - previousTenths;
}

export function observedSharesCopy(
  currentPeriod: string,
  currentShare: string,
  previousPeriod: string,
  previousShare: string,
): string {
  return `Observed values: ${previousShare} percent for the quarter starting ${previousPeriod}, and ${currentShare} percent for the quarter starting ${currentPeriod}.`;
}

export function calculatedDifferenceCopy(current: string, previous: string): string | null {
  const difference = shareDifferenceTenths(current, previous);
  if (difference === null) return null;
  const magnitude = (Math.abs(difference) / 10).toFixed(1);
  const movement =
    difference === 0 ? "unchanged from" : difference < 0 ? "lower than" : "higher than";
  const amount =
    difference === 0
      ? "The later stored share is"
      : `The later stored share is ${magnitude} percentage points`;
  return `Calculated difference: ${amount} ${movement} the earlier stored share. This arithmetic comparison is separate from the method calculation. It is not a forecast.`;
}

export function conditionalImplicationCopy(): string {
  return "Conditional implications: none are asserted. This survey balance does not measure lending volumes, output, prices, or portfolio weights.";
}

export function publicationGateCopy(): string {
  return "Not an investment conclusion. No price target, expected return, or fund recommendation is made. Publication remains closed. This internal reading has not passed the publication gate.";
}

function _tenths(value: string): number | null {
  const match = /^-?\d+(?:\.\d)?$/.exec(value.trim());
  if (!match) return null;
  const negative = value.trim().startsWith("-");
  const [whole, fraction = "0"] = value.trim().replace("-", "").split(".");
  const tenths = Number(whole) * 10 + Number(fraction);
  return negative ? -tenths : tenths;
}

export function sloosMonitorCopy(): string {
  return "The next Senior Loan Officer Opinion Survey. A changed value is stored as a new vintage and a new reading. The earlier reading is kept.";
}

export function sloosLimitationCopy(limitations: string[]): string {
  const stored = limitations.filter((item) => item.trim().length > 0);
  const vintage =
    "This file is the latest revised release. It is not a historical vintage panel, so the reading is not a point-in-time reconstruction.";
  return [...stored, vintage].join(" ");
}
