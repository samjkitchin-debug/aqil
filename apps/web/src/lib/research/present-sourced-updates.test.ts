import assert from "node:assert/strict";
import test from "node:test";

import {
  formatOptionalPublishedAt,
  latestRetrievedAt,
  presentSourcedUpdates,
  sortSourcedUpdatesByRecency,
  SOURCED_UPDATES_EMPTY_COPY,
} from "./present-sourced-updates.ts";
import type { SourcedUpdateV1 } from "./sourced-update.ts";

function fixture(partial: Partial<SourcedUpdateV1> & Pick<SourcedUpdateV1, "update_id">): SourcedUpdateV1 {
  return {
    schema_version: "1.0",
    source_id: "bls_employment_situation_archive",
    title: "Employment situation release",
    canonical_url: "https://www.bls.gov/news.release/empsit.toc.htm",
    published_at: "2026-01-10T13:30:00.000Z",
    retrieved_at: "2026-01-11T08:00:00.000Z",
    retrieval_id: "11111111-1111-4111-8111-111111111111",
    content_hash: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    correction_of: null,
    status: "sourced",
    ...partial,
  };
}

test("empty copy is exact for sourced updates", () => {
  assert.equal(
    SOURCED_UPDATES_EMPTY_COPY,
    "No sourced updates have been retrieved yet.",
  );
});

test("sorts by retrieved_at descending with stable tie-break", () => {
  const older = fixture({
    update_id: "00000000-0000-4000-8000-000000000001",
    retrieved_at: "2026-01-10T08:00:00.000Z",
  });
  const newer = fixture({
    update_id: "00000000-0000-4000-8000-000000000002",
    retrieved_at: "2026-01-12T08:00:00.000Z",
  });
  const sorted = sortSourcedUpdatesByRecency([older, newer]);
  assert.equal(sorted[0]?.update_id, newer.update_id);
  assert.equal(sorted[1]?.update_id, older.update_id);
  const sameRetrieval = sortSourcedUpdatesByRecency([
    fixture({
      update_id: "00000000-0000-4000-8000-000000000010",
      retrieved_at: "2026-10-21T20:37:00.000Z",
      published_at: "2026-01-09T13:30:00.000Z",
    }),
    fixture({
      update_id: "00000000-0000-4000-8000-000000000011",
      retrieved_at: "2026-10-21T20:37:00.000Z",
      published_at: "2026-10-02T11:51:00.000Z",
    }),
  ]);
  assert.equal(sameRetrieval[0]?.update_id, "00000000-0000-4000-8000-000000000011");
});

test("missing publication time stays blank in presentation", () => {
  const row = fixture({
    update_id: "00000000-0000-4000-8000-000000000003",
    published_at: null,
  });
  assert.equal(formatOptionalPublishedAt(row.published_at), null);
  const [presented] = presentSourcedUpdates([row]);
  assert.equal(presented?.publishedLabel, null);
});

test("latest retrieval comes from the newest row", () => {
  const rows = [
    fixture({
      update_id: "00000000-0000-4000-8000-000000000004",
      retrieved_at: "2026-01-09T08:00:00.000Z",
    }),
    fixture({
      update_id: "00000000-0000-4000-8000-000000000005",
      retrieved_at: "2026-01-15T08:00:00.000Z",
    }),
  ];
  assert.equal(latestRetrievedAt(rows), "2026-01-15T08:00:00.000Z");
});
