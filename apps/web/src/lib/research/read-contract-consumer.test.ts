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
  assert.match(copy.lines.join(" "), /Failed sources: example\.series/);
  assert.match(copy.lines.join(" "), /partial success/);
});

test("the health sentences keep each cycle outcome distinct", () => {
  const copy = describeOperationalState(
    {
      version: "1",
      startedAt: "2026-11-01T06:00:00.000Z",
      status: "partial",
      events: [
        { phase: "source", subjectId: "kept.series", outcome: "success", detail: "" },
        { phase: "source", subjectId: "same.series", outcome: "unchanged", detail: "" },
        { phase: "source", subjectId: "closed.series", outcome: "rights_blocked", detail: "" },
        { phase: "source", subjectId: "old.series", outcome: "stale", detail: "" },
        { phase: "method", subjectId: "QUIET", outcome: "skipped", detail: "" },
        { phase: "method", subjectId: "RUN", outcome: "success", detail: "" },
      ],
    },
    "2026-11-01",
  );
  const text = copy.lines.join("\n");
  assert.match(text, /Successful updates: kept\.series/);
  assert.match(text, /Unchanged sources: same\.series/);
  assert.match(text, /Blocked sources: closed\.series/);
  assert.match(text, /Skipped methodologies: QUIET/);
  assert.match(text, /Completed methodology runs: RUN/);
  assert.match(text, /Stale results: old\.series/);
});
