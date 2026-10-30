import "server-only";

import { connection } from "next/server";

import { resolveAccess } from "@/lib/auth/access";
import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import {
  extractPrivateResult,
  selectDisplayRun,
  type PrivateMethodologyResult,
  type StoredMethodologyRun,
} from "@/lib/research/private-methodology-result";

type RunRow = {
  run_id: string;
  method_id: string;
  method_version: string;
  executed_at: Date | string;
  execution_status: string;
  publication_allowed: boolean;
  data_sufficiency: string;
  analysis_mode: string;
  primary_dataset_id: string;
  missing_data_reason: string | null;
  statistical_interpretation: string;
  limitations: unknown;
  calculation: unknown;
};

export type LoadPrivateMethodologyResult =
  | { status: "ready"; result: PrivateMethodologyResult | null }
  | { status: "unavailable"; reason: string };

/**
 * Server read for a signed-in methodologies page.
 *
 * Signed-out and unverified sessions receive no calculation. The
 * publication_allowed column is returned unchanged and is not set true.
 */
export async function loadPrivateMethodologyResult(
  methodIds: readonly string[],
): Promise<LoadPrivateMethodologyResult> {
  const access = await resolveAccess();
  if (access.status !== "authenticated_authorised") {
    return { status: "ready", result: null };
  }
  await connection();
  if (methodIds.length === 0) return { status: "ready", result: null };
  const database = resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
  if (database.status === "unavailable") return database;
  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      const result = await client.query<RunRow>(
        `select run_id, method_id, method_version, executed_at, execution_status,
                publication_allowed, data_sufficiency, analysis_mode,
                primary_dataset_id, missing_data_reason, statistical_interpretation,
                limitations, calculation
         from research.research_runs
         where method_id = any($1::text[])
         order by executed_at desc`,
        [methodIds],
      );
      const runs = result.rows.map(toStoredRun);
      const selected = selectDisplayRun(runs);
      if (!selected.display) return { status: "ready", result: null };
      return {
        status: "ready",
        result: extractPrivateResult(selected.display, selected.unadoptedReestimate),
      };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "unavailable", reason: "The stored methodology result could not be read." };
  }
}

function toStoredRun(row: RunRow): StoredMethodologyRun {
  return {
    runId: row.run_id,
    methodId: row.method_id,
    methodVersion: row.method_version,
    executedAt: row.executed_at instanceof Date ? row.executed_at.toISOString() : row.executed_at,
    executionStatus: row.execution_status,
    publicationAllowed: row.publication_allowed === true,
    dataSufficiency: row.data_sufficiency,
    analysisMode: row.analysis_mode,
    primaryDatasetId: row.primary_dataset_id,
    missingDataReason: row.missing_data_reason,
    statisticalInterpretation: row.statistical_interpretation,
    limitations: limitationLines(row.limitations),
    calculation: isRecord(row.calculation) ? row.calculation : null,
  };
}

function limitationLines(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
