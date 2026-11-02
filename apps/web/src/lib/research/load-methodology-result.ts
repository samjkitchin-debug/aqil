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
import { readMethodologyCalculations } from "@/lib/research/read-contract";
import type { MethodologyRunRead } from "@/lib/research/read-contract-types";

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
  if (access.status !== "authenticated_authorised" || access.researchAuthorisation !== "founder") {
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
      const rows = await readMethodologyCalculations(client, methodIds);
      const runs = rows.map(toStoredRun);
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

function toStoredRun(row: MethodologyRunRead): StoredMethodologyRun {
  return {
    runId: row.runId,
    methodId: row.methodId,
    methodVersion: row.methodVersion,
    executedAt: row.executedAt,
    executionStatus: row.executionStatus,
    publicationAllowed: row.publicationAllowed,
    dataSufficiency: row.dataSufficiency,
    analysisMode: row.analysisMode,
    primaryDatasetId: row.primaryDatasetId,
    missingDataReason: row.missingDataReason,
    statisticalInterpretation: row.statisticalInterpretation,
    limitations: [...row.limitations],
    calculation: row.calculation,
  };
}
