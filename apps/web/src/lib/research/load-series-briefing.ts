import "server-only";

import { connection } from "next/server";

import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import type { LiveSeriesRetrieval } from "@/lib/research/present-series-briefing";

const SERIES_SOURCE_ID = "bls_cps_unemployment_rate";

type DbRow = {
  source_id: string;
  dataset_id: string;
  retrieved_at: Date | string;
  series_provenance: string;
  unit: string;
  seasonal_adjustment: string;
  frequency: string;
  period_start: Date | string;
  raw_value: string;
};

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

function toDateOnly(value: Date | string): string {
  if (value instanceof Date) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }
  return String(value).slice(0, 10);
}

export type LoadSeriesBriefingResult =
  | { status: "ok"; series: LiveSeriesRetrieval }
  | { status: "empty" }
  | { status: "unavailable"; reason: string };

export async function loadSeriesBriefing(): Promise<LoadSeriesBriefingResult> {
  await connection();
  const database = researchDatabaseUrl();
  if (database.status === "unavailable") return database;

  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      const result = await client.query<DbRow>(
        `select r.source_id, r.dataset_id, r.retrieved_at,
                o.series_provenance, o.unit, o.seasonal_adjustment, o.frequency,
                o.period_start, o.raw_value
         from research.economic_observations o
         join research.source_retrievals r on r.retrieval_id = o.retrieval_id
         where r.source_id = $1
           and r.collection_mode = 'live'
           and r.retrieval_id = (
             select retrieval_id
             from research.source_retrievals
             where source_id = $1 and collection_mode = 'live'
             order by retrieved_at desc
             limit 1
           )
         order by o.period_start`,
        [SERIES_SOURCE_ID],
      );
      if (result.rows.length === 0) return { status: "empty" };
      const latest = result.rows[result.rows.length - 1];
      if (!latest) return { status: "empty" };
      return {
        status: "ok",
        series: {
          sourceId: latest.source_id,
          datasetId: latest.dataset_id,
          retrievedAt: toIso(latest.retrieved_at),
          seriesProvenance: latest.series_provenance,
          unit: latest.unit,
          seasonalAdjustment: latest.seasonal_adjustment,
          frequency: latest.frequency,
          periods: result.rows.map((row) => toDateOnly(row.period_start)),
          latestPeriod: toDateOnly(latest.period_start),
          latestRawValue: latest.raw_value,
        },
      };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "empty" };
  }
}
