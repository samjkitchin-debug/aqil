import Link from "next/link";

import { METHODOLOGY_CATALOGUE, methodologyQueryIds } from "@/lib/research/methodology-catalogue";
import { loadMethodologyRuns } from "@/lib/research/load-methodology-runs";
import { presentMethodology, type MethodologyPresentation } from "@/lib/research/present-methodology";

export async function MethodologyOverviewSection() {
  const load = await loadMethodologyRuns(methodologyQueryIds());
  const items = METHODOLOGY_CATALOGUE.map((entry) => presentMethodology(entry, load));
  return (
    <div data-testid="methodology-overview">
      <p className="research-body intel-lead">
        Each card is one quantitative method. A stored run is described only as far as its publication state allows. Calculated output stays hidden while publication is closed.
      </p>
      <ul className="intel-method-list">
        {items.map((item) => (
          <li key={item.slug}>
            <MethodologyCard item={item} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function MethodologyCard({ item }: { item: MethodologyPresentation }) {
  return (
    <article className="intel-method-card">
      <h2 className="intel-method-name">
        <Link href={`/intelligence/methodologies/${item.slug}`} prefetch={false}>
          {item.name}
        </Link>
      </h2>
      <p className="research-body">{item.measures}</p>
      <dl className="intel-method-facts">
        <div>
          <dt>Domain</dt>
          <dd>{item.domain}</dd>
        </div>
        <div>
          <dt>Timing</dt>
          <dd>{item.timingLabel}</dd>
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
