import Link from "next/link";

import {
  METHODOLOGY_CATALOGUE,
  METHODOLOGY_GROUPS,
  methodologyQueryIds,
} from "@/lib/research/methodology-catalogue";
import { loadMethodologyRuns } from "@/lib/research/load-methodology-runs";
import { presentMethodology, type MethodologyPresentation } from "@/lib/research/present-methodology";

export async function MethodologyOverviewSection() {
  const load = await loadMethodologyRuns(methodologyQueryIds());
  const items = METHODOLOGY_CATALOGUE.map((entry) => ({
    entry,
    view: presentMethodology(entry, load),
  }));
  return (
    <div data-testid="methodology-overview">
      <p className="research-body intel-lead">
        Each card is one quantitative method. A stored run is described only as far as its publication state allows. A planned method has no calculation.
      </p>
      {METHODOLOGY_GROUPS.map((group) => {
        const groupItems = items.filter((item) => item.entry.group === group.id);
        if (groupItems.length === 0) return null;
        return (
          <section key={group.id} className="intel-method-group" aria-labelledby={`methods-${group.id}`}>
            <h2 id={`methods-${group.id}`} className="intel-section-title">
              {group.heading}
            </h2>
            <p className="research-meta">{group.note}</p>
            <ul className="intel-method-list">
              {groupItems.map((item) => (
                <li key={item.view.slug}>
                  <MethodologyCard item={item.view} planned={item.entry.stage === "planned"} />
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

function MethodologyCard({ item, planned }: { item: MethodologyPresentation; planned: boolean }) {
  return (
    <article className={planned ? "intel-method-card intel-method-card--planned" : "intel-method-card"}>
      <h3 className="intel-method-name">
        <Link href={`/intelligence/methodologies/${item.slug}`} prefetch={false}>
          {item.name}
        </Link>
      </h3>
      <p className="research-body">{item.measures}</p>
      <dl className="intel-method-facts">
        <div>
          <dt>Domain</dt>
          <dd>{item.domain}</dd>
        </div>
        <div>
          <dt>Function</dt>
          <dd>{item.functionLabel}</dd>
        </div>
        <div>
          <dt>Output</dt>
          <dd>{item.outputLabel}</dd>
        </div>
      </dl>
      <p className="research-meta" data-testid={`methodology-status-${item.slug}`}>
        {item.statusLine}
      </p>
      {item.latestLine ? <p className="research-meta">{item.latestLine}</p> : null}
      <p className="intel-method-open">
        <Link href={`/intelligence/methodologies/${item.slug}`} prefetch={false}>
          Open methodology
        </Link>
      </p>
    </article>
  );
}
