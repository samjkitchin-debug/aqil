import type { MacroEventInput, ThemeAssessmentInput } from "./macro-event-types.ts";

export const RESEARCH_AWARENESS_LINE =
  "Research awareness, not a forecast and not an investment instruction.";

export const PLAUSIBLE_CHANNEL_LABEL = "Plausible channel";

export const MATERIAL_DEVELOPMENT_DAYS = 45;

const SOURCE_LABELS: Record<string, string> = {
  govinfo_federal_register: "Federal Register via govinfo",
  federal_reserve_monetary_press: "Federal Reserve Board",
  ecb_monetary_press: "European Central Bank",
  sec_edgar_company_filings: "SEC EDGAR",
};

const DIMENSION_LABELS: Record<string, string> = {
  infrastructure_investment: "Infrastructure investment",
  commercial_adoption: "Commercial adoption",
  semiconductor_equipment_demand: "Semiconductor equipment demand",
  earnings_cash_flow: "Earnings and cash flow",
  market_breadth_relative_performance: "Market breadth and relative performance",
  financing_sustainability: "Financing sustainability",
};

export type PresentedChannel = {
  sourceId: string;
  href: string;
  label: string;
};

export type PresentedEvent = {
  eventKey: string;
  summary: string;
  reason: string | null;
  epistemicClass: string;
  claimScope: string;
  eventDate: string;
  datesStated: string;
  publishedDate: string;
  sourceLabel: string;
  sourceUrl: string | null;
  primaryTitle: string | null;
  later: string[];
  conflicting: string[];
  channels: PresentedChannel[];
};

export type PresentedDimension = {
  label: string;
  statusLine: string;
  measureLine: string;
  explanation: string;
  amountLine: string | null;
};

export type PresentedTheme = {
  assessmentId: string;
  supersededLine: string | null;
  establishes: string;
  doesNot: string[];
  dimensions: PresentedDimension[];
};

export type PresentedIntelligence = {
  title: string;
  awareness: string;
  empty: string | null;
  events: PresentedEvent[];
  themes: PresentedTheme[];
};

export function recordedEvents(events: readonly MacroEventInput[]): MacroEventInput[] {
  return events.filter((event) => event.recordClass === "recorded");
}

export function recordedThemes(
  themes: readonly ThemeAssessmentInput[],
): ThemeAssessmentInput[] {
  return themes.filter((theme) => theme.recordClass === "recorded");
}

export function evidenceStatusLine(
  status: ThemeAssessmentInput["dimensions"][number]["status"],
): string {
  if (status === "contradictory") return "The evidence is contradictory.";
  if (status === "insufficient" || status === "not_yet_monitored") {
    return "The evidence is missing.";
  }
  if (status === "stale") return "The evidence is stale.";
  return "The evidence is available for this dimension only.";
}

export function measureLine(
  kind: ThemeAssessmentInput["dimensions"][number]["measureKind"],
): string {
  if (kind === "equity_price") return "This figure is an equity price for the stated period.";
  if (kind === "actual_capital_expenditure") {
    return "This figure is company-wide actual capital expenditure.";
  }
  if (kind === "none") return "No measure is stored.";
  return "This measure is stored for this dimension only.";
}

export function plausibleChannelHref(sourceId: string): string {
  return `/conditions#macro-panel-${sourceId}`;
}

export function sourceLabel(sourceId: string): string {
  return SOURCE_LABELS[sourceId] ?? sourceId;
}

export function withinMaterialWindow(iso: string | null, asOf: Date): boolean {
  if (!iso) return false;
  const event = Date.parse(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(event)) return false;
  const today = Date.UTC(asOf.getUTCFullYear(), asOf.getUTCMonth(), asOf.getUTCDate());
  return Math.abs(today - event) / 86_400_000 <= MATERIAL_DEVELOPMENT_DAYS;
}

export function materialDevelopments(
  events: readonly MacroEventInput[],
  asOf: Date,
): MacroEventInput[] {
  const seen = new Set<string>();
  const cards: MacroEventInput[] = [];
  for (const event of recordedEvents(events)) {
    if (!event.surfaceOnToday || !event.surfaceReason?.trim()) continue;
    const published = event.evidence.find((item) => item.role === "primary")?.publishedAt ?? null;
    const inWindow =
      withinMaterialWindow(event.eventOn, asOf) || withinMaterialWindow(published, asOf);
    if (!inWindow || seen.has(event.eventKey)) continue;
    seen.add(event.eventKey);
    cards.push(event);
  }
  return cards;
}

export function presentMacroIntelligence(
  events: readonly MacroEventInput[],
  themes: readonly ThemeAssessmentInput[],
  variant: "today" | "compact" | "evidence",
  asOf: Date,
): PresentedIntelligence {
  const visibleEvents =
    variant === "today" ? materialDevelopments(events, asOf) : recordedEvents(events);
  const visibleThemes = variant === "today" ? [] : recordedThemes(themes);
  const superseded = new Set(
    visibleThemes
      .map((theme) => theme.supersedesAssessmentId)
      .filter((value): value is string => value !== null),
  );
  return {
    title: variant === "today" ? "Material developments" : "Events and themes",
    awareness: RESEARCH_AWARENESS_LINE,
    empty:
      visibleEvents.length === 0 && visibleThemes.length === 0
        ? variant === "today"
          ? "No material development is recorded for this window."
          : "No event or theme assessment is recorded."
        : null,
    events: visibleEvents.map(presentEvent),
    themes: [...visibleThemes]
      .sort((a, b) => a.recordedAt.localeCompare(b.recordedAt))
      .map((theme) => presentTheme(theme, superseded.has(theme.assessmentId))),
  };
}

export function presentedCopy(page: PresentedIntelligence): string {
  return JSON.stringify(page);
}

function presentEvent(event: MacroEventInput): PresentedEvent {
  const primary = event.evidence.find((item) => item.role === "primary") ?? null;
  return {
    eventKey: event.eventKey,
    summary: event.summary,
    reason: event.surfaceReason,
    epistemicClass: epistemicLabel(event.epistemicClass),
    claimScope: claimLabel(event.claimScope),
    eventDate: formatDate(event.eventOn),
    datesStated: event.eventDatesStated,
    publishedDate: formatDate(primary?.publishedAt ?? null),
    sourceLabel: primary ? sourceLabel(primary.sourceId) : "Source not stored",
    sourceUrl: primary?.canonicalUrl ?? null,
    primaryTitle: primary?.title ?? null,
    later: event.evidence
      .filter((item) => item.role === "subsequent_development")
      .map((item) => item.title),
    conflicting: event.evidence
      .filter((item) => item.role === "conflicting")
      .map((item) => item.title),
    channels: event.indicatorSourceIds.map((sourceId) => ({
      sourceId,
      href: plausibleChannelHref(sourceId),
      label: PLAUSIBLE_CHANNEL_LABEL,
    })),
  };
}

function presentTheme(theme: ThemeAssessmentInput, superseded: boolean): PresentedTheme {
  return {
    assessmentId: theme.assessmentId,
    supersededLine: superseded
      ? "This assessment was superseded. The earlier row is unchanged."
      : null,
    establishes: theme.realEconomyActivity,
    doesNot: [theme.earnings, theme.marketPrices, theme.mediaAttention],
    dimensions: theme.dimensions.map((dimension) => ({
      label: DIMENSION_LABELS[dimension.dimension] ?? dimension.dimension,
      statusLine: evidenceStatusLine(dimension.status),
      measureLine: measureLine(dimension.measureKind),
      explanation: dimension.explanation,
      amountLine:
        dimension.amount && dimension.unit
          ? `${dimension.amount} ${dimension.unit}`
          : null,
    })),
  };
}

function epistemicLabel(value: MacroEventInput["epistemicClass"]): string {
  if (value === "confirmed_event") return "Confirmed event";
  if (value === "reported_allegation") return "Reported allegation";
  if (value === "forecast") return "Forecast";
  return "Interpretation";
}

function claimLabel(value: MacroEventInput["claimScope"]): string {
  return value === "policy_action_stated" ? "Policy action stated" : "Publication recorded";
}

export function formatDate(iso: string | null): string {
  if (!iso) return "Date not stated";
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(date.getTime())) return "Date not stated";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}
