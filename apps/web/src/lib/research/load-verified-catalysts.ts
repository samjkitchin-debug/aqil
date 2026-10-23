import "server-only";

import { connection } from "next/server";

import { resolveResearchDatabaseUrl } from "@/lib/data/private-database-url";
import { OPERATIONAL_CALENDAR_FILTER } from "@/lib/research/operational-sources";
import type { VerifiedCatalyst } from "@/lib/research/present-verified-catalysts";

type DbRow = {
  event_id: string;
  title: string;
  scheduled_at: Date | string;
  timezone: string | null;
  status: string;
  source_id: string;
  source_locator: string | null;
  last_verified_at: Date | string;
  date_precision: string;
};

function researchDatabaseUrl() {
  return resolveResearchDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.RESEARCH_DATABASE_URL,
  });
}

export type LoadVerifiedCatalystsResult =
  | { status: "ready"; events: VerifiedCatalyst[] }
  | { status: "unavailable"; reason: string };

function toIso(value: Date | string): string {
  if (value instanceof Date) return value.toISOString();
  return value;
}

export async function loadVerifiedCatalysts(): Promise<LoadVerifiedCatalystsResult> {
  await connection();
  const database = researchDatabaseUrl();
  if (database.status === "unavailable") return database;
  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: database.url });
    await client.connect();
    try {
      const result = await client.query<DbRow>(
        `select event_id, title, scheduled_at, timezone, status, source_id,
                source_locator, last_verified_at, date_precision
         from forward.catalyst_events
         where ${OPERATIONAL_CALENDAR_FILTER}
           and date_precision = 'confirmed'
           and scheduled_at > now()
         order by scheduled_at`,
      );
      return {
        status: "ready",
        events: result.rows.flatMap((row) => {
          if (!row.source_locator?.startsWith("https://")) return [];
          return [
            {
              eventId: row.event_id,
              title: row.title,
              scheduledAt: toIso(row.scheduled_at),
              timezone: row.timezone ?? "",
              status: row.status,
              sourceId: row.source_id,
              sourceLocator: row.source_locator,
              lastVerifiedAt: toIso(row.last_verified_at),
              datePrecision: row.date_precision,
            },
          ];
        }),
      };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "ready", events: [] };
  }
}
