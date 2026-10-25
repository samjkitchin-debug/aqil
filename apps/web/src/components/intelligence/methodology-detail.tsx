import Link from "next/link";

import { methodologyBySlug } from "@/lib/research/methodology-catalogue";
import { loadMethodologyRuns } from "@/lib/research/load-methodology-runs";
import { presentMethodology } from "@/lib/research/present-methodology";

const TECHNICAL_ID = "technical";

export async function MethodologyDetail({ slug }: { slug: string }) {
  const entry = methodologyBySlug(slug);
  if (!entry) return null;
  const load = await loadMethodologyRuns(entry.queryMethodIds);
  const view = presentMethodology(entry, load);
  const narrative = view.sections.filter((section) => section.id !== TECHNICAL_ID);
  const technical = view.sections.find((section) => section.id === TECHNICAL_ID);
  return (
    <article data-testid="methodology-detail">
      <p className="research-meta">
        <Link href="/intelligence/methodologies" prefetch={false}>
          All methodologies
        </Link>
      </p>
      <h2 className="intel-region-title">{view.name}</h2>
      <dl className="intel-method-facts">
        <div>
          <dt>Domain</dt>
          <dd>{view.domain}</dd>
        </div>
        <div>
          <dt>Timing</dt>
          <dd>{view.timingLabel}</dd>
        </div>
        <div>
          <dt>Output</dt>
          <dd>{view.outputLabel}</dd>
        </div>
      </dl>
      <p className="research-body" data-testid="methodology-detail-status">
        {view.statusLine}
      </p>
      {narrative.map((section) => (
        <section key={section.id} aria-labelledby={`method-${section.id}`} className="intel-method-section">
          <h3 id={`method-${section.id}`} className="intel-section-title">
            {section.heading}
          </h3>
          {section.paragraphs.map((paragraph) => (
            <p key={paragraph} className="research-body">
              {paragraph}
            </p>
          ))}
        </section>
      ))}
      {view.references.length > 0 ? (
        <section aria-labelledby="method-references" className="intel-method-section">
          <h3 id="method-references" className="intel-section-title">
            References
          </h3>
          <ul className="intel-reference-list">
            {view.references.map((reference) => (
              <li key={reference.href}>
                <a href={reference.href} rel="noopener noreferrer" target="_blank">
                  {reference.label}
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {technical ? (
        <details className="macro-details">
          <summary>{technical.heading}</summary>
          {technical.paragraphs.map((paragraph) => (
            <p key={paragraph} className="research-meta">
              {paragraph}
            </p>
          ))}
        </details>
      ) : null}
    </article>
  );
}
