import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { MACRO_SERIES } from "./macro-conditions.ts";
import { INDICATOR_METADATA } from "./indicator-metadata.ts";

const RIGHTS_PATH = fileURLToPath(new URL("../../../../../docs/sources/SOURCE_RIGHTS.csv", import.meta.url));

test("every tracked series has copy and a verified source link", () => {
  assert.deepEqual(
    INDICATOR_METADATA.map((item) => item.sourceId),
    MACRO_SERIES.map((item) => item.sourceId),
  );
  const rights = readFileSync(RIGHTS_PATH, "utf8");
  const rows = rights.split(/\r?\n/).filter((line) => line.length > 0);
  for (const item of INDICATOR_METADATA) {
    assert.ok(item.measures.length > 40, item.sourceId);
    assert.ok(item.matters.length > 40, item.sourceId);
    assert.ok(item.organisation.length > 0);
    assert.ok(item.datasetLabel.length > 0);
    assert.equal(item.measures.includes("because"), false);
    const row = rows.find((line) => line.startsWith(`${item.sourceId},`));
    assert.ok(row, item.sourceId);
    assert.ok(row.includes(item.sourceHref), `${item.sourceId} href`);
    if (item.retrievalHref) assert.ok(row.includes(item.retrievalHref), `${item.sourceId} retrieval`);
  }
});
