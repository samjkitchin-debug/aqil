import assert from "node:assert/strict";
import test from "node:test";

import {
  CAPTURE_SENTENCE,
  FROZEN_NOT_QUALIFIED_REASONS,
  NOT_QUALIFIED_SUMMARY,
  PROSPECTIVE_ASSESSMENT_HEADING,
  PROSPECTIVE_REASONS_HEADING,
  PUBLICATION_SENTENCE,
  presentProspectiveAssessment,
  type ProspectiveAssessmentRecord,
} from "./present-prospective-assessment.ts";

const record: ProspectiveAssessmentRecord = {
  assessmentId: "pa-fixture",
  capturedAt: "2026-10-23T09:50:00.000Z",
  lifecycleStatus: "not_qualified",
  publicationAllowed: false,
  horizonMonths: null,
  captureNote: "Stored at capture. not a reconstruction of dates before captured_at.",
};

function visibleText(record: ProspectiveAssessmentRecord): string {
  const presented = presentProspectiveAssessment(record);
  assert.ok(presented);
  return [
    presented.heading,
    presented.summary,
    presented.reasonsHeading,
    ...presented.reasons,
    presented.capture,
    presented.publication,
    presented.capturedOn,
  ].join(" ");
}

test("prospective assessment headings stay in sentence case", () => {
  assert.equal(PROSPECTIVE_ASSESSMENT_HEADING, "Prospective assessment");
  assert.equal(PROSPECTIVE_REASONS_HEADING, "Reasons");
});

test("a not qualified assessment stays internal and states the frozen reasons", () => {
  const presented = presentProspectiveAssessment(record);
  assert.ok(presented);
  assert.equal(presented.summary, NOT_QUALIFIED_SUMMARY);
  assert.equal(
    presented.summary,
    "The reading is internal. No 6- or 12-month hypothesis qualified.",
  );
  assert.deepEqual(presented.reasons, [
    "No vintage panel.",
    "No identified mechanism.",
    "The stored windows do not share one horizon.",
  ]);
  assert.deepEqual(presented.reasons, FROZEN_NOT_QUALIFIED_REASONS);
  assert.equal(presented.capture, CAPTURE_SENTENCE);
  assert.equal(
    presented.capture,
    "The frozen baseline is the snapshot stored at capture. This snapshot is not a reconstruction of dates before it was captured.",
  );
  assert.equal(presented.publication, PUBLICATION_SENTENCE);
  assert.equal(presented.capturedOn, "23 October 2026");
  const text = visibleText(record);
  assert.match(text, /The reading is internal\./);
  assert.match(text, /No 6- or 12-month hypothesis qualified\./);
  assert.match(text, /No vintage panel\./);
  assert.match(text, /No identified mechanism\./);
  assert.match(text, /The stored windows do not share one horizon\./);
  assert.equal(
    /\b(composite score|direction|probability|return|recommendation)\b/i.test(text),
    false,
  );
});

test("a stored horizon and extra capture wording stay off the page", () => {
  const text = visibleText({
    ...record,
    horizonMonths: 12,
    captureNote:
      "not a reconstruction of dates before captured_at. Direction higher. Probability 70 percent. Expected return 5 percent. Recommendation hold.",
  });
  assert.match(text, /No 6- or 12-month hypothesis qualified\./);
  assert.equal(text.includes("Direction"), false);
  assert.equal(text.includes("Probability"), false);
  assert.equal(text.includes("return"), false);
  assert.equal(text.includes("Recommendation"), false);
  assert.equal(text.includes("5 percent"), false);
});

test("only a closed not qualified row is presented", () => {
  assert.equal(
    presentProspectiveAssessment({ ...record, lifecycleStatus: "proposed_internal" }),
    null,
  );
  assert.equal(presentProspectiveAssessment({ ...record, lifecycleStatus: "evaluated" }), null);
  assert.equal(presentProspectiveAssessment({ ...record, lifecycleStatus: "superseded" }), null);
  assert.equal(presentProspectiveAssessment({ ...record, publicationAllowed: true }), null);
  assert.equal(
    presentProspectiveAssessment({ ...record, captureNote: "latest revised only" }),
    null,
  );
});
