import "server-only";

import { connection } from "next/server";

import { resolveAccess } from "@/lib/auth/access";
import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import type { MethodologyRunMeta } from "@/lib/research/present-methodology";

type RunRow = {
  method_id: string;
  method_version: string;
  executed_at: Date | string;
  execution_status: string;
  publication_allowed: boolean;
  data_sufficiency: string;
  calculation_stored: boolean;
};

export type LoadMethodologyRunsResult =
  | { status: "ready"; runs: MethodologyRunMeta[] }
  | { status: "unavailable"; reason: string };

function researchDatabaseUrl() {
  return resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
}

/**
 * Read run metadata for the methodologies list.
 * The calculation JSON is not selected. A signed-in detail page loads it separately.
 */
export async function loadMethodologyRuns(
  methodIds: readonly string[],
): Promise<LoadMethodologyRunsResult> {
  await connection();
  if (methodIds.length === 0) return { status: "ready", runs: [] };
  const access = await resolveAccess();
  const includeStoredFlag = access.status === "authenticated_authorised";
  const database = researchDatabaseUrl();
  if (database.status === "unavailable") return database;
  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      const result = await client.query<RunRow>(
        `select method_id, method_version, executed_at, execution_status,
                publication_allowed, data_sufficiency,
                ${includeStoredFlag ? "(calculation is not null)" : "false"} as calculation_stored
         from research.research_runs
         where method_id = any($1::text[])
         order by executed_at desc`,
        [methodIds],
      );
      return {
        status: "ready",
        runs: result.rows.map((row) => ({
          methodId: row.method_id,
          methodVersion: row.method_version,
          executedAt: executedAt(row.executed_at),
          executionStatus: row.execution_status,
          publicationAllowed: row.publication_allowed === true,
          dataSufficiency: row.data_sufficiency,
          calculationStored: row.calculation_stored === true,
        })),
      };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "unavailable", reason: "Methodology run metadata could not be read." };
  }
}

function executedAt(value: Date | string): string {
  if (value instanceof Date) return value.toISOString();
  return value;
}
