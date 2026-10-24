import Link from "next/link";

import {
  ECONOMIC_READING_HEADING,
  type EconomicEvidenceView,
  type FamilyBrief,
} from "@/lib/research/present-economic-evidence";

type Props = {
  view: EconomicEvidenceView;
};

export function EconomicEvidenceBriefing({ view }: Props) {
  return (
    <section className="economic-briefing" aria-labelledby="economic-reading-heading" data-testid="economic-reading">
      <h3 id="economic-reading-heading" className="research-section-title">
        {ECONOMIC_READING_HEADING}
      </h3>
      <p className="research-body" data-testid="economic-reading-intro">
        This reading restates stored results. It does not calculate a new change. The reading is internal.
      </p>
      {view.overall ? (
        <p className="research-body" data-testid="economic-reading-overall">
          {view.overall}
        </p>
      ) : null}
      <p className="research-meta" data-testid="economic-reading-method">
        Method {view.methodId} {view.methodVersion}.
        {view.runId ? ` Run ${view.runId}.` : " No stored run."}
        {view.payloadHash ? ` Payload ${view.payloadHash}.` : null}{" "}
        <Link href="/research" prefetch={false} data-testid="economic-reading-evidence">
          Evidence
        </Link>
        .
      </p>
      {view.families.map((family) => (
        <FamilyBlock key={family.id} family={family} />
      ))}
      <p className="research-body" data-testid="economic-hicp-note">
        {view.hicpNote}
      </p>
      <h3 className="research-section-title">{view.unansweredHeading}</h3>
      <ul className="macro-detail-list" data-testid="economic-unanswered">
        {view.unanswered.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <p className="research-body">{view.unansweredNote}</p>
      {view.limitations.length > 0 ? (
        <>
          <h3 className="research-section-title">Stored limitations</h3>
          <ul className="macro-detail-list" data-testid="economic-limitations">
            {view.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function FamilyBlock({ family }: { family: FamilyBrief }) {
  return (
    <section aria-labelledby={`economic-family-${family.id}`} data-testid={`economic-family-${family.id}`}>
      <h4 id={`economic-family-${family.id}`} className="macro-panel-title">
        {family.label}
      </h4>
      <Field label="Observation" text={family.observation} />
      <Field label="Trend" text={family.trend} />
      <Field label="Context" text={family.context} />
      <Field label="Reading" text={family.reading} />
      <Field label="Contradiction" text={family.contradiction} />
      <Field label="Limitation" text={family.limitation} />
      <p className="research-body">
        <span className="macro-heading">Next. </span>
        {family.nextHref ? (
          <>
            {family.next}{" "}
            <Link href={family.nextHref} prefetch={false} data-testid={`economic-next-${family.id}`}>
              Upcoming
            </Link>
            .
          </>
        ) : (
          family.next
        )}
      </p>
    </section>
  );
}

function Field({ label, text }: { label: string; text: string }) {
  return (
    <p className="research-body">
      <span className="macro-heading">{label}. </span>
      {text}
    </p>
  );
}
