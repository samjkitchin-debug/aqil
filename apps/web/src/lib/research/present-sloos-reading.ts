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

export function sloosMonitorCopy(): string {
  return "The next Senior Loan Officer Opinion Survey. A changed value is stored as a new vintage and a new reading. The earlier reading is kept.";
}

export function sloosLimitationCopy(limitations: string[]): string {
  const stored = limitations.filter((item) => item.trim().length > 0);
  const vintage =
    "This file is the latest revised release. It is not a historical vintage panel, so the reading is not a point-in-time reconstruction.";
  return [...stored, vintage].join(" ");
}
