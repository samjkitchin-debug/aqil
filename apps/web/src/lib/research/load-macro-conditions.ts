import "server-only";

import { connection } from "next/server";

import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import {
  MACRO_CONDITIONS_WINDOW,
  MACRO_SERIES,
  type StoredSeriesWindow,
} from "@/lib/research/macro-conditions";

type DbRow = {
  source_id: string;
  dataset_id: string;
  retrieved_at: Date | string;
  series_provenance: string | null;
  unit: string;
  seasonal_adjustment: string;
  frequency: string;
  period_start: string;
  raw_value: string;
};

const WINDOW_SQL = `
with ranked as (
  select distinct on (r.source_id, o.period_start)
    r.source_id,
    o.dataset_id,
    r.retrieved_at,
    o.series_provenance,
    o.unit,
    o.seasonal_adjustment,
    o.frequency,
    o.period_start::text as period_start,
    o.raw_value::text as raw_value
  from research.economic_observations o
  join research.source_retrievals r using (retrieval_id)
  where r.collection_mode = 'live'
    and r.source_id = any($1::text[])
  order by r.source_id, o.period_start desc,
           o.provider_vintage_date desc nulls last,
           r.retrieved_at desc
),
windowed as (
  select ranked.*,
         row_number() over (partition by source_id order by period_start desc) as recency
  from ranked
)
select source_id, dataset_id, retrieved_at, series_provenance, unit,
       seasonal_adjustment, frequency, period_start, raw_value
from windowed
where recency <= $2
order by source_id, period_start
`;

export type LoadMacroConditionsResult =
  | { status: "ok"; series: StoredSeriesWindow[] }
  | { status: "unavailable"; reason: string };

function researchDatabaseUrl() {
  return resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
}

function toIso(value: Date | string): string {
  if (value instanceof Date) return value.toISOString();
  return value;
}

function groupRows(rows: readonly DbRow[]): StoredSeriesWindow[] {
  const bySource = new Map<string, { series: StoredSeriesWindow; latestPeriod: string }>();
  for (const row of rows) {
    const period = row.period_start.slice(0, 10);
    const rawValue = row.raw_value.trim();
    if (!period || !rawValue) continue;
    let entry = bySource.get(row.source_id);
    if (!entry) {
      entry = {
        latestPeriod: period,
        series: {
          sourceId: row.source_id,
          datasetId: row.dataset_id,
          retrievedAt: toIso(row.retrieved_at),
          seriesProvenance: row.series_provenance,
          unit: row.unit,
          seasonalAdjustment: row.seasonal_adjustment,
          frequency: row.frequency,
          observations: [],
        },
      };
      bySource.set(row.source_id, entry);
    }
    entry.series.observations.push({ period, rawValue });
    if (period >= entry.latestPeriod) {
      entry.latestPeriod = period;
      entry.series.datasetId = row.dataset_id;
      entry.series.seriesProvenance = row.series_provenance;
      entry.series.unit = row.unit;
      entry.series.seasonalAdjustment = row.seasonal_adjustment;
      entry.series.frequency = row.frequency;
    }
    const retrievedAt = toIso(row.retrieved_at);
    if (!entry.series.retrievedAt || retrievedAt > entry.series.retrievedAt) {
      entry.series.retrievedAt = retrievedAt;
    }
  }
  return [...bySource.values()].map((entry) => entry.series);
}

export async function loadMacroConditions(): Promise<LoadMacroConditionsResult> {
  await connection();
  const database = researchDatabaseUrl();
  if (database.status === "unavailable") return database;

  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      await client.query("begin read only");
      const result = await client.query<DbRow>(WINDOW_SQL, [
        MACRO_SERIES.map((series) => series.sourceId),
        MACRO_CONDITIONS_WINDOW,
      ]);
      await client.query("commit");
      return { status: "ok", series: groupRows(result.rows) };
    } catch (error) {
      await client.query("rollback").catch(() => undefined);
      throw error;
    } finally {
      await client.end();
    }
  } catch {
    return { status: "unavailable", reason: "The research database could not be read." };
  }
}
