/** Present the stored comparison of the four macro readings. */

export const MACRO_READING_HEADING = "Macro reading";
export const CITED_CHANGES_HEADING = "Cited changes";
export const LIMITATIONS_HEADING = "Limitations";

const INTERNAL_SENTENCE = "The reading is internal.";

export type MacroReadingView = {
  summary: string;
  citedChanges: string[];
  limitations: string[];
  methodId: string;
  methodVersion: string;
  runId: string;
  payloadHash: string;
  analysisMode: string;
};

export function presentMacroReading(view: MacroReadingView): {
  summary: string;
  citedChanges: string[];
  limitations: string;
} {
  return {
    summary: withInternalSentence(view.summary),
    citedChanges: view.citedChanges.filter((item) => item.trim().length > 0),
    limitations: withInternalSentence(
      view.limitations.filter((item) => item.trim().length > 0).join(" "),
    ),
  };
}

function withInternalSentence(text: string): string {
  const trimmed = text.trim();
  if (trimmed.includes(INTERNAL_SENTENCE)) return trimmed;
  if (!trimmed) return INTERNAL_SENTENCE;
  return `${trimmed} ${INTERNAL_SENTENCE}`;
}
