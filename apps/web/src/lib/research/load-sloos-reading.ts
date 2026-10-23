import "server-only";

import { connection } from "next/server";

import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import {
  describeStoredSloosSeries,
  type SloosReadingView,
} from "@/lib/research/present-sloos-reading";

type RunRow = {
  run_id: string;
  execution_status: string;
  data_sufficiency: string;
  missing_data_reason: string | null;
  narrative: string | null;
  calculation: {
    net_tightening_share_percent?: string;
    observation_period?: string;
    direction_label?: string;
  } | null;
  statistical_interpretation: string | null;
  limitations: string[] | null;
  method_id: string;
  method_version: string;
  analytical_payload_hash: string | null;
  observation_ids: string[] | null;
  analysis_mode: string;
  dataset_id: string;
  source_id: string;
};

type ObservationRow = {
  observation_id: string;
  raw_value: string;
  period_start: string;
  retrieved_at: string;
  collection_mode: string;
};

export type LoadSloosReadingResult =
  | { status: "ready"; reading: SloosReadingView }
  | { status: "unavailable"; reason: string }
  | { status: "empty" };

function researchDatabaseUrl() {
  return resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
}

export async function loadSloosReading(): Promise<LoadSloosReadingResult> {
  await connection();
  const database = researchDatabaseUrl();
  if (database.status === "unavailable") return database;
  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      const runResult = await client.query<RunRow>(
        `select run_id, execution_status, data_sufficiency, missing_data_reason,
                narrative, calculation, statistical_interpretation, limitations,
                method_id, method_version, analytical_payload_hash, observation_ids,
                analysis_mode, primary_dataset_id as dataset_id, source_id
         from research.research_runs
         where method_id = 'SLOOS_CIL_LENDING_STANDARDS'
           and execution_status in ('completed', 'completed_insufficient')
         order by executed_at desc
         limit 1`,
      );
      const run = runResult.rows[0];
      if (!run) return { status: "empty" };
      if (run.execution_status !== "completed" || run.data_sufficiency !== "sufficient") {
        return {
          status: "unavailable",
          reason: run.missing_data_reason ?? "The stored reading is not sufficient.",
        };
      }
      const observationId = run.observation_ids?.[0];
      if (!observationId || !run.calculation?.observation_period) {
        return { status: "unavailable", reason: "The stored reading has no cited observation." };
      }
      const observation = await client.query<ObservationRow>(
        `select o.observation_id, o.raw_value, o.period_start::text as period_start,
                o.retrieved_at::text as retrieved_at, r.collection_mode
         from research.economic_observations o
         join research.source_retrievals r using (retrieval_id)
         where o.observation_id = $1`,
        [observationId],
      );
      const cited = observation.rows[0];
      if (!cited || cited.collection_mode !== "live") {
        return { status: "unavailable", reason: "The cited observation is not a live retrieval." };
      }
      const previous = await client.query<ObservationRow>(
        `select o.observation_id, o.raw_value, o.period_start::text as period_start,
                o.retrieved_at::text as retrieved_at, r.collection_mode
         from research.economic_observations o
         join research.source_retrievals r using (retrieval_id)
         where o.dataset_id = $1
           and r.collection_mode = 'live'
           and o.period_start < $2::date
         order by o.period_start desc, o.provider_vintage_date desc
         limit 1`,
        [run.dataset_id, cited.period_start],
      );
      const prior = previous.rows[0] ?? null;
      const history = await client.query<{ period_start: string; raw_value: string }>(
        `select distinct on (o.period_start)
                o.period_start::text as period_start, o.raw_value
         from research.economic_observations o
         join research.source_retrievals r using (retrieval_id)
         where o.dataset_id = $1
           and r.collection_mode = 'live'
         order by o.period_start, o.provider_vintage_date desc nulls last, o.retrieved_at desc`,
        [run.dataset_id],
      );
      const stored = describeStoredSloosSeries(
        history.rows.map((row) => ({
          period: row.period_start,
          sharePercent: row.raw_value,
        })),
      );
      return {
        status: "ready",
        reading: {
          narrative: run.narrative ?? "",
          sharePercent: run.calculation.net_tightening_share_percent ?? cited.raw_value,
          observationPeriod: run.calculation.observation_period ?? cited.period_start,
          directionLabel: run.calculation.direction_label ?? "",
          interpretation: run.statistical_interpretation ?? "",
          limitations: run.limitations ?? [],
          previousPeriod: prior?.period_start ?? null,
          previousSharePercent: prior?.raw_value ?? null,
          sourceId: run.source_id,
          datasetId: run.dataset_id,
          methodId: run.method_id,
          methodVersion: run.method_version,
          runId: run.run_id,
          payloadHash: run.analytical_payload_hash ?? "",
          observationId: cited.observation_id,
          retrievedAt: cited.retrieved_at,
          analysisMode: run.analysis_mode,
          storedHistory: stored?.history ?? null,
          storedPosition: stored?.position ?? null,
          contradiction: stored?.contradiction ?? null,
        },
      };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "empty" };
  }
}
