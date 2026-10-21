import { providerLabelForSource } from "./present-sourced-updates.ts";

export type VerifiedCatalyst = {
  eventId: string;
  title: string;
  scheduledAt: string;
  timezone: string;
  status: string;
  sourceId: string;
  sourceLocator: string;
  lastVerifiedAt: string;
  datePrecision: string;
};

export type CatalystPresentation = {
  event: VerifiedCatalyst;
  providerLabel: string;
  scheduleLabel: string;
  verifiedLabel: string;
  zoneLabel: string;
};

const WINDOW_MS = 120 * 24 * 60 * 60 * 1000;

const SCHEDULED = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/New_York",
});

const VERIFIED = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

export function upcomingCatalysts(
  events: readonly VerifiedCatalyst[],
  now: Date = new Date(),
): { listed: CatalystPresentation[]; laterCount: number } {
  const confirmed = events
    .filter((event) => event.datePrecision === "confirmed" && event.sourceLocator.startsWith("https://"))
    .filter((event) => {
      const when = Date.parse(event.scheduledAt);
      return !Number.isNaN(when) && when > now.getTime();
    })
    .sort((a, b) => Date.parse(a.scheduledAt) - Date.parse(b.scheduledAt));
  const windowEnd = now.getTime() + WINDOW_MS;
  const listed = confirmed.filter((event) => Date.parse(event.scheduledAt) <= windowEnd);
  return {
    listed: listed.map(presentCatalyst),
    laterCount: confirmed.length - listed.length,
  };
}

function presentCatalyst(event: VerifiedCatalyst): CatalystPresentation {
  const when = new Date(event.scheduledAt);
  const zoneLabel = event.timezone === "America/New_York" ? "Eastern Time" : event.timezone;
  const clock =
    event.timezone === "America/New_York" ? SCHEDULED.format(when) : event.scheduledAt;
  return {
    event,
    providerLabel: providerLabelForSource(event.sourceId),
    scheduleLabel: `${clock} ${zoneLabel}`,
    verifiedLabel: `${VERIFIED.format(new Date(event.lastVerifiedAt))} UTC`,
    zoneLabel,
  };
}
