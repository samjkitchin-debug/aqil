import {
  CITED_CHANGES_HEADING,
  LIMITATIONS_HEADING,
  MACRO_READING_HEADING,
  presentMacroReading,
  type MacroReadingView,
} from "@/lib/research/present-macro-reading";

type Props = {
  reading: MacroReadingView;
};

export function MacroReadingPanel({ reading }: Props) {
  const presented = presentMacroReading(reading);
  return (
    <section aria-labelledby="macro-reading-heading" data-testid="macro-reading">
      <h2 id="macro-reading-heading" className="research-section-title">
        {MACRO_READING_HEADING}
      </h2>
      <p className="research-body">{presented.summary}</p>
      <h3 className="research-section-title">{CITED_CHANGES_HEADING}</h3>
      {presented.citedChanges.map((change) => (
        <p className="research-body mt-[var(--space-3)]" key={change}>
          {change}
        </p>
      ))}
      <h3 className="research-section-title">{LIMITATIONS_HEADING}</h3>
      <p className="research-body">{presented.limitations}</p>
      <p className="research-meta">
        Method {reading.methodId} {reading.methodVersion}. Analysis mode {reading.analysisMode}. Run{" "}
        {reading.runId}. Payload {reading.payloadHash.slice(0, 16)}…. The reading is internal.
        Publication remains closed.
      </p>
    </section>
  );
}
