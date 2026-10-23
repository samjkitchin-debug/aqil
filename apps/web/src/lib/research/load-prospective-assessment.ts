import "server-only";

import { connection } from "next/server";

import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import {
  presentProspectiveAssessment,
  type ProspectiveAssessmentRecord,
} from "@/lib/research/present-prospective-assessment";

type AssessmentRow = {
  assessment_id: string;
  captured_at: string;
  lifecycle_status: string;
  publication_allowed: boolean;
  horizon_months: number | null;
  capture_note: string;
};

export type LoadProspectiveAssessmentResult =
  | { status: "ready"; assessment: ProspectiveAssessmentRecord }
  | { status: "empty" }
  | { status: "unavailable"; reason: string };

function researchDatabaseUrl() {
  return resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
}

function toRecord(row: AssessmentRow): ProspectiveAssessmentRecord | null {
  if (row.lifecycle_status !== "not_qualified") return null;
  if (row.publication_allowed !== false) return null;
  const horizon = row.horizon_months;
  if (horizon !== null && horizon !== 6 && horizon !== 12) return null;
  return {
    assessmentId: row.assessment_id,
    capturedAt: row.captured_at,
    lifecycleStatus: "not_qualified",
    publicationAllowed: false,
    horizonMonths: horizon,
    captureNote: row.capture_note,
  };
}

export async function loadProspectiveAssessment(): Promise<LoadProspectiveAssessmentResult> {
  await connection();
  const database = researchDatabaseUrl();
  if (database.status === "unavailable") return database;
  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      const result = await client.query<AssessmentRow>(
        `select assessment_id,
                captured_at::text as captured_at,
                lifecycle_status,
                publication_allowed,
                horizon_months,
                capture_note
         from research.prospective_assessments
         where lifecycle_status = 'not_qualified'
           and publication_allowed = false
         order by captured_at desc
         limit 1`,
      );
      const row = result.rows[0];
      if (!row) return { status: "empty" };
      const assessment = toRecord(row);
      if (!assessment || !presentProspectiveAssessment(assessment)) return { status: "empty" };
      return { status: "ready", assessment };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "empty" };
  }
}
