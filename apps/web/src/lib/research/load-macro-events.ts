import "server-only";

import { connection } from "next/server";

import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import type {
  DimensionStatus,
  EvidenceRole,
  MacroEventInput,
  MeasureKind,
  ThemeAssessmentInput,
} from "@/lib/research/macro-event-types";

type EventRow = {
  event_id: string;
  event_key: string;
  category: string;
  epistemic_class: MacroEventInput["epistemicClass"];
  claim_scope: MacroEventInput["claimScope"];
  summary: string;
  event_on: Date | string;
  event_dates_stated: string;
  indicator_source_ids: string[] | null;
  channel_note: string | null;
  surface_on_today: boolean;
  surface_reason: string | null;
  surfaced_at: Date | string | null;
  record_class: MacroEventInput["recordClass"];
  investment_implication: MacroEventInput["investmentImplication"];
};

type EvidenceRow = {
  event_id: string;
  role: EvidenceRole;
  cluster_key: string;
  title: string;
  canonical_url: string;
  published_at: Date | string | null;
  source_id: string;
};

type ThemeRow = {
  assessment_id: string;
  recorded_at: Date | string;
  supersedes_assessment_id: string | null;
  record_class: ThemeAssessmentInput["recordClass"];
  real_economy_activity: string;
  earnings: string;
  market_prices: string;
  media_attention: string;
};

type DimensionRow = {
  assessment_id: string;
  dimension: string;
  status: DimensionStatus;
  measure_kind: MeasureKind;
  explanation: string;
  amount: string | null;
  unit: string | null;
  period_start: Date | string | null;
  period_end: Date | string | null;
  reporting_entity: string | null;
  relationship: "supports" | "contradicts" | null;
  canonical_url: string | null;
};

export type LoadMacroIntelligenceResult =
  | { status: "ok"; events: MacroEventInput[]; themes: ThemeAssessmentInput[] }
  | { status: "empty" }
  | { status: "unavailable"; reason: string };

function researchDatabaseUrl() {
  return resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
}

function day(value: Date | string | null): string | null {
  if (value === null) return null;
  if (value instanceof Date) {
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const date = String(value.getDate()).padStart(2, "0");
    return `${value.getFullYear()}-${month}-${date}`;
  }
  return value.slice(0, 10);
}

function instant(value: Date | string | null): string | null {
  if (value === null) return null;
  if (value instanceof Date) return value.toISOString();
  return value;
}

export async function loadMacroIntelligence(): Promise<LoadMacroIntelligenceResult> {
  await connection();
  const database = researchDatabaseUrl();
  if (database.status === "unavailable") return database;

  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      const events = await client.query<EventRow>(
        `select event_id, event_key, category, epistemic_class, claim_scope, summary,
                event_on, event_dates_stated, indicator_source_ids, channel_note,
                surface_on_today, surface_reason, surfaced_at, record_class,
                investment_implication
         from research.macro_events
         where record_class = 'recorded'
         order by event_on desc, recorded_at desc`,
      );
      const evidence = await client.query<EvidenceRow>(
        `select ev.event_id, ev.role, ev.cluster_key, u.title, u.canonical_url,
                u.published_at, u.source_id
         from research.macro_event_evidence ev
         join research.macro_events e on e.event_id = ev.event_id
         join research.sourced_updates u on u.update_id = ev.update_id
         where e.record_class = 'recorded'`,
      );
      const themes = await client.query<ThemeRow>(
        `select assessment_id, recorded_at, supersedes_assessment_id, record_class,
                real_economy_activity, earnings, market_prices, media_attention
         from research.theme_assessments
         where record_class = 'recorded'
         order by recorded_at asc`,
      );
      const dimensions = await client.query<DimensionRow>(
        `select d.assessment_id, d.dimension, d.status, d.measure_kind, d.explanation,
                d.amount, d.unit, d.period_start, d.period_end, d.reporting_entity,
                d.relationship, u.canonical_url
         from research.theme_dimension_evidence d
         join research.theme_assessments a on a.assessment_id = d.assessment_id
         left join research.sourced_updates u on u.update_id = d.update_id
         where a.record_class = 'recorded'`,
      );
      const evidenceByEvent = new Map<string, EvidenceRow[]>();
      for (const row of evidence.rows) {
        const list = evidenceByEvent.get(row.event_id) ?? [];
        list.push(row);
        evidenceByEvent.set(row.event_id, list);
      }
      const dimensionsByTheme = new Map<string, DimensionRow[]>();
      for (const row of dimensions.rows) {
        const list = dimensionsByTheme.get(row.assessment_id) ?? [];
        list.push(row);
        dimensionsByTheme.set(row.assessment_id, list);
      }
      const mappedEvents = events.rows.map((row) => mapEvent(row, evidenceByEvent));
      const mappedThemes = themes.rows.map((row) => mapTheme(row, dimensionsByTheme));
      if (mappedEvents.length === 0 && mappedThemes.length === 0) return { status: "empty" };
      return { status: "ok", events: mappedEvents, themes: mappedThemes };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "empty" };
  }
}

function mapEvent(row: EventRow, evidenceByEvent: Map<string, EvidenceRow[]>): MacroEventInput {
  return {
    eventId: row.event_id,
    eventKey: row.event_key,
    category: row.category,
    epistemicClass: row.epistemic_class,
    claimScope: row.claim_scope,
    summary: row.summary,
    eventOn: day(row.event_on) ?? "",
    eventDatesStated: row.event_dates_stated,
    indicatorSourceIds: row.indicator_source_ids ?? [],
    channelNote: row.channel_note,
    surfaceOnToday: row.surface_on_today,
    surfaceReason: row.surface_reason,
    surfacedAt: instant(row.surfaced_at),
    recordClass: row.record_class,
    investmentImplication: row.investment_implication,
    evidence: (evidenceByEvent.get(row.event_id) ?? []).map((item) => ({
      role: item.role,
      clusterKey: item.cluster_key,
      title: item.title,
      canonicalUrl: item.canonical_url,
      publishedAt: instant(item.published_at),
      sourceId: item.source_id,
    })),
  };
}

function mapTheme(
  row: ThemeRow,
  dimensionsByTheme: Map<string, DimensionRow[]>,
): ThemeAssessmentInput {
  return {
    assessmentId: row.assessment_id,
    recordedAt: instant(row.recorded_at) ?? "",
    supersedesAssessmentId: row.supersedes_assessment_id,
    recordClass: row.record_class,
    realEconomyActivity: row.real_economy_activity,
    earnings: row.earnings,
    marketPrices: row.market_prices,
    mediaAttention: row.media_attention,
    dimensions: (dimensionsByTheme.get(row.assessment_id) ?? []).map((item) => ({
      dimension: item.dimension,
      status: item.status,
      measureKind: item.measure_kind,
      explanation: item.explanation,
      amount: item.amount,
      unit: item.unit,
      periodStart: day(item.period_start),
      periodEnd: day(item.period_end),
      reportingEntity: item.reporting_entity,
      relationship: item.relationship,
      sourceUrl: item.canonical_url,
    })),
  };
}
