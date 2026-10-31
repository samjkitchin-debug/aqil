import assert from "node:assert/strict";
import test from "node:test";

import { describeOperationalState } from "./read-contract-consumer.ts";
import { RESEARCH_READ_CONTRACT_VERSION } from "./read-contract-types.ts";

test("an unknown cycle says today's cycle has not run", () => {
  const copy = describeOperationalState(null, "2026-11-01");
  assert.equal(copy.version, RESEARCH_READ_CONTRACT_VERSION);
  assert.equal(copy.headline, "Today's cycle has not run.");
  assert.match(copy.lines.join(" "), /last valid result/i);
});

test("a failed source is named and the contract version stays 1", () => {
  const copy = describeOperationalState(
    {
      version: "1",
      startedAt: "2026-11-01T06:00:00.000Z",
      status: "partial",
      events: [
        { phase: "source", subjectId: "example.series", outcome: "failed", detail: "timeout" },
      ],
    },
    "2026-11-01",
  );
  assert.equal(copy.headline, "Today's cycle has a record.");
  assert.match(copy.lines.join(" "), /example\.series failed/);
});
