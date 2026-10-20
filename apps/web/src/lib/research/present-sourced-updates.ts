import type { SourcedUpdateV1 } from "@/lib/research/sourced-update";

export const SOURCED_UPDATES_EMPTY_COPY =
  "No sourced updates have been retrieved yet.";

export const CALENDAR_EMPTY_COPY =
  "No validated catalyst date has been retrieved.";

export const EXPLORE_EMPTY_COPY =
  "No authoritative exposure mapping has been retrieved.";

const PROVIDER_LABELS: Record<string, string> = {
  bls_cps_unemployment_rate: "U.S. Bureau of Labor Statistics",
  bls_employment_situation_archive: "U.S. Bureau of Labor Statistics",
};

export function providerLabelForSource(sourceId: string): string {
  return PROVIDER_LABELS[sourceId] ?? sourceId;
}

/** Newest retrieval first; ties break on update_id for stable ordering. */
export function sortSourcedUpdatesByRecency(updates: SourcedUpdateV1[]): SourcedUpdateV1[] {
  return [...updates].sort((a, b) => {
    const retrieved = Date.parse(b.retrieved_at) - Date.parse(a.retrieved_at);
    if (retrieved !== 0) return retrieved;
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
