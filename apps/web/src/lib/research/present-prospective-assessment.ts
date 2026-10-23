/** Plain-language presentation of one stored prospective assessment. */

export const PROSPECTIVE_ASSESSMENT_HEADING = "Prospective assessment";
export const PROSPECTIVE_REASONS_HEADING = "Reasons";

export const NOT_QUALIFIED_SUMMARY =
  "The reading is internal. No 6- or 12-month hypothesis qualified.";

export const FROZEN_NOT_QUALIFIED_REASONS = [
  "No vintage panel.",
  "No identified mechanism.",
  "The stored windows do not share one horizon.",
] as const;

export const CAPTURE_SENTENCE =
  "This row is what was stored at capture. It is not a reconstruction of dates before captured_at.";

export const PUBLICATION_SENTENCE = "Publication remains closed.";

const REQUIRED_CAPTURE_PHRASE = "not a reconstruction of dates before captured_at";

export type ProspectiveLifecycleStatus =
  | "not_qualified"
  | "proposed_internal"
  | "superseded"
  | "evaluated";

export type ProspectiveAssessmentRecord = {
  assessmentId: string;
  capturedAt: string;
  lifecycleStatus: ProspectiveLifecycleStatus;
  publicationAllowed: boolean;
  horizonMonths: 6 | 12 | null;
  captureNote: string;
};

export type ProspectiveAssessmentPresentation = {
  heading: string;
  reasonsHeading: string;
  summary: string;
  reasons: readonly string[];
  capture: string;
  publication: string;
  capturedOn: string;
};

export function presentProspectiveAssessment(
  record: ProspectiveAssessmentRecord,
): ProspectiveAssessmentPresentation | null {
  if (record.lifecycleStatus !== "not_qualified") return null;
  if (record.publicationAllowed !== false) return null;
  if (!record.assessmentId.trim()) return null;
  if (!record.captureNote.includes(REQUIRED_CAPTURE_PHRASE)) return null;
  return {
    heading: PROSPECTIVE_ASSESSMENT_HEADING,
    reasonsHeading: PROSPECTIVE_REASONS_HEADING,
    summary: NOT_QUALIFIED_SUMMARY,
    reasons: FROZEN_NOT_QUALIFIED_REASONS,
    capture: CAPTURE_SENTENCE,
    publication: PUBLICATION_SENTENCE,
    capturedOn: capturedOnLabel(record.capturedAt),
  };
}

export function capturedOnLabel(isoTimestamp: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(isoTimestamp.trim());
  if (!match) return isoTimestamp.trim();
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}
