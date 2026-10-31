import "server-only";

import { connection } from "next/server";

import { resolveAccess } from "@/lib/auth/access";
import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import type { MethodologyRunMeta } from "@/lib/research/present-methodology";
import { readMethodologyRunMetadata } from "@/lib/research/read-contract";

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
      const rows = await readMethodologyRunMetadata(client, methodIds, includeStoredFlag);
      return {
        status: "ready",
        runs: rows.map((row) => ({
          methodId: row.methodId,
          methodVersion: row.methodVersion,
          executedAt: row.executedAt,
          executionStatus: row.executionStatus,
          publicationAllowed: row.publicationAllowed,
          dataSufficiency: row.dataSufficiency,
          calculationStored: row.calculationStored === true,
        })),
      };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "unavailable", reason: "Methodology run metadata could not be read." };
  }
}

