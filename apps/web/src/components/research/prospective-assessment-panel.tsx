import {
  presentProspectiveAssessment,
  type ProspectiveAssessmentRecord,
} from "@/lib/research/present-prospective-assessment";

type Props = {
  assessment: ProspectiveAssessmentRecord;
};

export function ProspectiveAssessmentPanel({ assessment }: Props) {
  const presented = presentProspectiveAssessment(assessment);
  if (!presented) return null;
  return (
    <section aria-labelledby="prospective-assessment-heading" data-testid="prospective-assessment">
      <h2 id="prospective-assessment-heading" className="research-section-title">
        {presented.heading}
      </h2>
      <p className="research-body">{presented.summary}</p>
      <h3 className="research-section-title">{presented.reasonsHeading}</h3>
      {presented.reasons.map((reason) => (
        <p className="research-body mt-[var(--space-3)]" key={reason}>
          {reason}
        </p>
      ))}
      <p className="research-body mt-[var(--space-3)]">{presented.capture}</p>
      <p className="research-meta">
        Assessment {assessment.assessmentId}. Captured {presented.capturedOn}. The reading is
        internal. {presented.publication}
      </p>
    </section>
  );
}
