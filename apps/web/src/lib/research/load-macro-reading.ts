import "server-only";

import { connection } from "next/server";

import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import type { MacroReadingView } from "@/lib/research/present-macro-reading";

type RunRow = {
  run_id: string;
  execution_status: string;
  data_sufficiency: string;
  missing_data_reason: string | null;
  narrative: string | null;
  calculation: {
    summary?: string;
    cited_changes?: string[];
    limitations?: string[];
  } | null;
  limitations: string[] | null;
  method_id: string;
  method_version: string;
  analytical_payload_hash: string | null;
  analysis_mode: string;
};

export type LoadMacroReadingResult =
  | { status: "ready"; reading: MacroReadingView }
  | { status: "unavailable"; reason: string }
  | { status: "empty" };

function researchDatabaseUrl() {
  return resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
}

export async function loadMacroReading(): Promise<LoadMacroReadingResult> {
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
                narrative, calculation, limitations, method_id, method_version,
                analytical_payload_hash, analysis_mode
         from research.research_runs
         where method_id = 'MACRO_READING_SYNTHESIS'
           and execution_status in ('completed', 'completed_insufficient')
         order by executed_at desc
         limit 1`,
      );
      const run = runResult.rows[0];
      if (!run) return { status: "empty" };
      const summary = run.calculation?.summary || run.narrative || "";
      const cited = run.calculation?.cited_changes ?? [];
      const limitations = run.calculation?.limitations ?? run.limitations ?? [];
      if (!summary.trim()) {
        return {
          status: "unavailable",
          reason: run.missing_data_reason ?? "The stored reading has no summary.",
        };
      }
      return {
        status: "ready",
        reading: {
          summary,
          citedChanges: cited,
          limitations,
          methodId: run.method_id,
          methodVersion: run.method_version,
          runId: run.run_id,
          payloadHash: run.analytical_payload_hash ?? "",
          analysisMode: run.analysis_mode,
        },
      };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "empty" };
  }
}
