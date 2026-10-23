import assert from "node:assert/strict";
import test from "node:test";

import {
  CITED_CHANGES_HEADING,
  LIMITATIONS_HEADING,
  MACRO_READING_HEADING,
  presentMacroReading,
} from "./present-macro-reading.ts";

const view = {
  summary:
    "The reading is internal. Labour, prices, production, and credit stay separate. No composite score is calculated.",
  citedChanges: [
    "Unemployment was 4.2 percent in September 2026 (observation ln-fixture).",
    "Federal funds was 3.50 percent per year. The 10-year yield was 4.25 percent per year. Federal funds and the 10-year yield stay separate levels.",
  ],
  limitations: [
    "The reading is internal.",
    "Their difference is not calculated. No real rate is calculated.",
    "Euro-area HICP is excluded and ends in December 2025.",
    "Industrial production is not a GDP figure.",
    "Coincident changes are not a cause.",
  ],
  methodId: "MACRO_READING_SYNTHESIS",
  methodVersion: "1.0.0",
  runId: "synthesis-fixture",
  payloadHash: "abc123",
  analysisMode: "latest_revised",
};

test("macro reading headings stay in sentence case", () => {
  assert.equal(MACRO_READING_HEADING, "Macro reading");
  assert.equal(CITED_CHANGES_HEADING, "Cited changes");
  assert.equal(LIMITATIONS_HEADING, "Limitations");
});

test("macro reading copy stays internal and does not add a score", () => {
  const presented = presentMacroReading(view);
  const text = [presented.summary, ...presented.citedChanges, presented.limitations].join(" ");
  assert.match(presented.summary, /The reading is internal\./);
  assert.match(text, /No composite score is calculated\./);
  assert.match(text, /Their difference is not calculated\./);
  assert.match(text, /No real rate is calculated\./);
  assert.match(text, /ends in December 2025/);
  assert.match(text, /not a GDP figure/);
  assert.match(text, /not a cause/);
  assert.equal(text.includes("0.75"), false);
  assert.equal(text.includes("near-term forward"), false);
  assert.equal(presented.citedChanges.length, 2);
});

test("a summary without the internal sentence gains it", () => {
  const presented = presentMacroReading({
    ...view,
    summary: "Labour and prices share September 2026.",
    limitations: ["Publication remains closed."],
  });
  assert.match(presented.summary, /The reading is internal\./);
  assert.match(presented.limitations, /The reading is internal\./);
  assert.match(presented.limitations, /Publication remains closed\./);
});
