import "server-only";

import { connection } from "next/server";

import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import { OPERATIONAL_CALENDAR_FILTER } from "@/lib/research/operational-sources";
import {
  SERIES_SOURCE,
  type EconomicEvidenceInput,
  type StoredMethodRun,
} from "@/lib/research/present-economic-evidence";

const RUNS = [
  ["LABOUR_MARKET_CONDITIONS", "1.1.0"],
  ["PRICES_AND_POLICY", "1.1.0"],
  ["INDUSTRIAL_PRODUCTION_ACTIVITY", "1.1.0"],
  ["CREDIT_STANDARDS_AND_VOLUMES", "1.0.0"],
  ["MACRO_READING_SYNTHESIS", "1.0.0"],
] as const;

const BLS_TITLE_SOURCES: Record<string, readonly string[]> = {
  "Employment Situation": [SERIES_SOURCE.unemployment, SERIES_SOURCE.payrolls],
  "Consumer Price Index": [SERIES_SOURCE.cpi],
  "Job Openings and Labor Turnover Survey": [SERIES_SOURCE.openings],
};

type RunRow = {
  run_id: string;
  data_sufficiency: string;
  missing_data_reason: string | null;
  calculation: unknown;
  limitations: unknown;
  method_id: string;
  method_version: string;
  analytical_payload_hash: string | null;
  analysis_mode: string | null;
};

export type LoadEconomicEvidenceResult =
  | { status: "ready"; input: EconomicEvidenceInput }
  | { status: "unavailable"; reason: string };

function researchDatabaseUrl() {
  return resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
}

/** Read the latest stored family runs. This does not insert a run. */
export async function loadEconomicEvidence(): Promise<LoadEconomicEvidenceResult> {
  await connection();
  const database = researchDatabaseUrl();
  if (database.status === "unavailable") return database;
  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      const runResult = await client.query<RunRow>(
        `select distinct on (method_id)
            run_id, data_sufficiency, missing_data_reason,
            calculation, limitations, method_id, method_version,
            analytical_payload_hash, analysis_mode
         from research.research_runs
         where (method_id, method_version) in (
           ('LABOUR_MARKET_CONDITIONS', '1.1.0'),
           ('PRICES_AND_POLICY', '1.1.0'),
           ('INDUSTRIAL_PRODUCTION_ACTIVITY', '1.1.0'),
           ('CREDIT_STANDARDS_AND_VOLUMES', '1.0.0'),
           ('MACRO_READING_SYNTHESIS', '1.0.0')
         )
           and execution_status in ('completed', 'completed_insufficient')
         order by method_id, executed_at desc`,
      );
      let titles: string[] = [];
      try {
        const calendar = await client.query<{ title: string }>(
          `select distinct title
           from forward.catalyst_events
           where ${OPERATIONAL_CALENDAR_FILTER}
             and date_precision = 'confirmed'
             and scheduled_at > now()`,
        );
        titles = calendar.rows.map((row) => row.title);
      } catch {
        titles = [];
      }
      const byId = new Map(runResult.rows.map((row) => [row.method_id, toRun(row)]));
      return {
        status: "ready",
        input: {
          synthesis: byId.get("MACRO_READING_SYNTHESIS") ?? null,
          labour: byId.get("LABOUR_MARKET_CONDITIONS") ?? null,
          prices: byId.get("PRICES_AND_POLICY") ?? null,
          production: byId.get("INDUSTRIAL_PRODUCTION_ACTIVITY") ?? null,
          credit: byId.get("CREDIT_STANDARDS_AND_VOLUMES") ?? null,
          blsCalendarSourceIds: calendarSourceIds(titles),
        },
      };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "unavailable", reason: "The stored economic reading could not be read." };
  }
}

function toRun(row: RunRow): StoredMethodRun {
  const known = RUNS.some(([methodId, version]) => methodId === row.method_id && version === row.method_version);
  return {
    methodId: row.method_id,
    methodVersion: row.method_version,
    runId: row.run_id,
    payloadHash: row.analytical_payload_hash ?? "",
    dataSufficiency: known ? row.data_sufficiency : "insufficient",
    missingDataReason: row.missing_data_reason,
    analysisMode: row.analysis_mode,
    calculation: calculationOf(row.calculation),
    limitations: stringList(row.limitations),
  };
}

function calendarSourceIds(titles: readonly string[]): string[] {
  const ids: string[] = [];
  for (const title of titles) {
    const sources = BLS_TITLE_SOURCES[title];
    if (!sources) continue;
    for (const sourceId of sources) {
      if (!ids.includes(sourceId)) ids.push(sourceId);
    }
  }
  return ids;
}

function calculationOf(value: unknown): Record<string, unknown> | null {
  if (typeof value === "string") {
    try {
      return calculationOf(JSON.parse(value) as unknown);
    } catch {
      return null;
    }
  }
  return isRecord(value) ? value : null;
}

function stringList(value: unknown): string[] {
  if (typeof value === "string") {
    try {
      return stringList(JSON.parse(value) as unknown);
    } catch {
      return [];
    }
  }
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
