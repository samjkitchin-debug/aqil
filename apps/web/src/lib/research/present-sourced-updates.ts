import type { SourcedUpdateV1 } from "@/lib/research/sourced-update";

export const SOURCED_UPDATES_EMPTY_COPY =
  "No sourced updates have been retrieved yet.";

export const PUBLICATION_BOUNDARY =
  "These are the publishers' releases. They are not an Aqil investment conclusion.";

export const NO_PUBLISHER_CORRECTION =
  "No publisher correction is stored. A later correction is kept as a new row when the publisher changes the page.";

export const CALENDAR_EMPTY_COPY =
  "No validated catalyst date has been retrieved.";

export const EXPLORE_EMPTY_COPY =
  "No authoritative exposure mapping has been retrieved.";

const PROVIDER_LABELS: Record<string, string> = {
  bls_cps_unemployment_rate: "U.S. Bureau of Labor Statistics",
  bls_employment_situation_archive: "U.S. Bureau of Labor Statistics",
  bls_ics_schedule: "U.S. Bureau of Labor Statistics",
  federal_reserve_monetary_press: "Federal Reserve Board",
  bls_cpi_archive: "U.S. Bureau of Labor Statistics",
  ecb_monetary_press: "European Central Bank",
};

/** A publisher date inside this window can be shown as a recent publication. */
export const RECENT_PUBLICATION_DAYS = 14;

export function publisherCorrectionLine(
  updates: readonly { correction_of: string | null }[],
): string | null {
  if (updates.length === 0 || updates.some((row) => row.correction_of)) return null;
  return NO_PUBLISHER_CORRECTION;
}

export function providerLabelForSource(sourceId: string): string {
  return PROVIDER_LABELS[sourceId] ?? sourceId;
}

/** Newest retrieval first; ties break on update_id for stable ordering. */
export function sortSourcedUpdatesByRecency(updates: SourcedUpdateV1[]): SourcedUpdateV1[] {
  return [...updates].sort((a, b) => {
    const retrieved = Date.parse(b.retrieved_at) - Date.parse(a.retrieved_at);
    if (retrieved !== 0) return retrieved;
    const publishedA = a.published_at === null ? Number.NEGATIVE_INFINITY : Date.parse(a.published_at);
    const publishedB = b.published_at === null ? Number.NEGATIVE_INFINITY : Date.parse(b.published_at);
    if (publishedA !== publishedB) return publishedB - publishedA;
    return b.update_id.localeCompare(a.update_id);
  });
}

export function latestRetrievedAt(updates: SourcedUpdateV1[]): string | null {
  if (updates.length === 0) return null;
  const sorted = sortSourcedUpdatesByRecency(updates);
  return sorted[0]?.retrieved_at ?? null;
}

export function hasSourcedUpdates(updates: SourcedUpdateV1[]): boolean {
  return updates.length > 0;
}

/**
 * Publication time for display. Null stays blank — never substitute retrieved_at.
 */
export function formatOptionalPublishedAt(iso: string | null): string | null {
  if (iso === null || iso.trim() === "") return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(date);
}

export function formatRetrievedAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(date);
}

/** Future publication times stated by the source (not inferred schedule). */
export function futureSourcePublishedDates(
  updates: SourcedUpdateV1[],
  now: Date = new Date(),
): SourcedUpdateV1[] {
  const nowMs = now.getTime();
  return sortSourcedUpdatesByRecency(updates).filter((row) => {
    if (row.published_at === null) return false;
    const publishedMs = Date.parse(row.published_at);
    return !Number.isNaN(publishedMs) && publishedMs > nowMs;
  });
}

export type SourcedUpdatePresentation = {
  update: SourcedUpdateV1;
  providerLabel: string;
  publishedLabel: string | null;
  retrievedLabel: string;
};

export function presentSourcedUpdate(row: SourcedUpdateV1): SourcedUpdatePresentation {
  return {
    update: row,
    providerLabel: providerLabelForSource(row.source_id),
    publishedLabel: formatOptionalPublishedAt(row.published_at),
    retrievedLabel: formatRetrievedAt(row.retrieved_at),
  };
}

export function presentSourcedUpdates(
  updates: SourcedUpdateV1[],
): SourcedUpdatePresentation[] {
  return sortSourcedUpdatesByRecency(updates).map(presentSourcedUpdate);
}

export function partitionPublications(
  updates: SourcedUpdateV1[],
  now: Date = new Date(),
): { recent: SourcedUpdatePresentation[]; earlier: SourcedUpdatePresentation[] } {
  const cutoff = now.getTime() - RECENT_PUBLICATION_DAYS * 24 * 60 * 60 * 1000;
  const recent: SourcedUpdateV1[] = [];
  const earlier: SourcedUpdateV1[] = [];
  for (const row of updates) {
    const published = row.published_at === null ? Number.NaN : Date.parse(row.published_at);
    if (!Number.isNaN(published) && published >= cutoff && published <= now.getTime()) {
      recent.push(row);
    } else {
      earlier.push(row);
    }
  }
  const byPublished = (rows: SourcedUpdateV1[]) =>
    [...rows].sort((a, b) => {
      const aMs = a.published_at === null ? Number.NEGATIVE_INFINITY : Date.parse(a.published_at);
      const bMs = b.published_at === null ? Number.NEGATIVE_INFINITY : Date.parse(b.published_at);
      if (aMs !== bMs) return bMs - aMs;
      return b.update_id.localeCompare(a.update_id);
    });
  return {
    recent: byPublished(recent).map(presentSourcedUpdate),
    earlier: byPublished(earlier).map(presentSourcedUpdate),
  };
}
