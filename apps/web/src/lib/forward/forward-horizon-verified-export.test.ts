import { readFile } from "node:fs/promises";
import path from "node:path";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { validateForwardHorizon } from "./validate-forward-horizon.ts";

const VERIFIED_MACRO_PATH = path.join(
  process.cwd(),
  "fixtures",
  "forward-horizon-verified-macro.v1.json",
);

describe("verified macro horizon export contract", () => {
  it("validates the database-exported verified macro bundle", async () => {
    const raw = await readFile(VERIFIED_MACRO_PATH, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    assert.equal(validateForwardHorizon(parsed), true);
    assert.equal(
      (parsed as { data_mode: string }).data_mode,
      "verified_source",
    );
  });
});
