import "server-only";

import { connection } from "next/server";

import type { SourcedUpdateV1 } from "@/lib/research/sourced-update";

const DEFAULT_RESEARCH_DATABASE_URL =
  "postgresql://research_worker:research_worker@127.0.0.1:54322/postgres";

const LIST_LIMIT = 24;

type DbRow = {
  update_id: string;
  schema_version: string;
  source_id: string;
  title: string;
  canonical_url: string;
  published_at: Date | string | null;
  retrieved_at: Date | string;
  retrieval_id: string;
  content_hash: string;
  correction_of: string | null;
  status: string;
};

function researchDatabaseUrl(): string {
  return process.env.RESEARCH_DATABASE_URL?.trim() || DEFAULT_RESEARCH_DATABASE_URL;
}

function toIso(value: Date | string | null): string | null {
  if (value === null) return null;
  if (value instanceof Date) return value.toISOString();
  return value;
}

export function mapSourcedUpdateRow(row: DbRow): SourcedUpdateV1 {
  const publishedAt = toIso(row.published_at);
  const retrievedAt = toIso(row.retrieved_at);
  if (!retrievedAt) {
    throw new Error("sourced update row missing retrieved_at");
  }
  return {
    schema_version: "1.0",
    update_id: row.update_id,
    source_id: row.source_id,
    title: row.title,
    canonical_url: row.canonical_url,
    published_at: publishedAt,
    retrieved_at: retrievedAt,
    retrieval_id: row.retrieval_id,
    content_hash: row.content_hash,
    correction_of: row.correction_of,
    status: "sourced",
  };
}

export type LoadSourcedUpdatesResult =
  | { status: "ok"; updates: SourcedUpdateV1[] }
  | { status: "empty" };

export async function loadSourcedUpdates(): Promise<LoadSourcedUpdatesResult> {
  await connection();

  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: researchDatabaseUrl() });
    await client.connect();
    try {
      const result = await client.query<DbRow>(
        `select update_id, schema_version, source_id, title, canonical_url,
                published_at, retrieved_at, retrieval_id, content_hash, correction_of, status
         from research.sourced_updates
         order by retrieved_at desc
         limit $1`,
        [LIST_LIMIT],
      );
      const updates = result.rows.map(mapSourcedUpdateRow);
      if (updates.length === 0) {
        return { status: "empty" };
      }
      return { status: "ok", updates };
    } finally {
      await client.end();
    }
  } catch {
    return { status: "empty" };
  }
}
