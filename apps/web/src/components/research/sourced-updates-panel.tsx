import Link from "next/link";

import {
  formatRetrievedAt,
  latestRetrievedAt,
  partitionPublications,
  PUBLICATION_BOUNDARY,
  publisherCorrectionLine,
  RECENT_PUBLICATION_DAYS,
  type SourcedUpdatePresentation,
  SOURCED_UPDATES_EMPTY_COPY,
} from "@/lib/research/present-sourced-updates";
import type { SourcedUpdateV1 } from "@/lib/research/sourced-update";

type Props = {
  updates: SourcedUpdateV1[];
  variant: "briefing" | "evidence";
};

export function SourcedUpdatesPanel({ updates, variant }: Props) {
  if (updates.length === 0) {
    return (
      <div className="research-banner" data-testid="sourced-updates-empty">
        <p className="research-body">{SOURCED_UPDATES_EMPTY_COPY}</p>
      </div>
    );
  }

  const groups = partitionPublications(updates);
  const lastRetrieval = latestRetrievedAt(updates);
  const correctionLine = publisherCorrectionLine(updates);

  return (
    <section data-testid="sourced-updates-panel">
      <p className="research-body" data-testid="publication-boundary">
        {PUBLICATION_BOUNDARY}
      </p>
      {correctionLine ? (
        <p className="research-body" data-testid="no-publisher-correction">
          {correctionLine}
        </p>
      ) : null}
      <p className="research-meta" data-testid="sourced-updates-freshness">
        {updates.length} sourced {updates.length === 1 ? "publication" : "publications"}
        {lastRetrieval ? (
          <>
            {" "}
            · Last successful retrieval {formatRetrievedAt(lastRetrieval)}
          </>
        ) : null}
      </p>
      {groups.recent.length > 0 ? (
        <PublicationGroup
          testId="recent-publications"
          label={`Published in the last ${RECENT_PUBLICATION_DAYS} days`}
          rows={groups.recent}
          variant={variant}
        />
      ) : (
        <p className="research-body" data-testid="no-recent-publications">
          No stored publication was published in the last {RECENT_PUBLICATION_DAYS} days.
        </p>
      )}
      {groups.earlier.length > 0 ? (
        <PublicationGroup
          testId="earlier-publications"
          label="Earlier publications"
          note="These are the publishers' release dates. An older release is not a new announcement."
          rows={groups.earlier}
          variant={variant}
        />
      ) : null}
    </section>
  );
}

function PublicationGroup({
  testId,
  label,
  note,
  rows,
  variant,
}: {
  testId: string;
  label: string;
  note?: string;
  rows: SourcedUpdatePresentation[];
  variant: "briefing" | "evidence";
}) {
  return (
    <div data-testid={testId}>
      <p className="research-meta">{label}</p>
      {note ? <p className="research-body">{note}</p> : null}
      <ul className="forward-horizon-list">
        {rows.map((row) => (
          <li key={row.update.update_id} className="forward-horizon-item">
            <div className="forward-horizon-item-head">
              <span className="forward-horizon-date">
                {row.publishedLabel ?? "Publication time not stated"}
              </span>
              <span className="forward-horizon-materiality">{row.providerLabel}</span>
            </div>
            <h3 className="forward-horizon-title">
              <Link href={row.update.canonical_url} rel="noopener noreferrer" target="_blank">
                {row.update.title}
              </Link>
            </h3>
            <p className="research-meta">
              Retrieved {row.retrievedLabel} · Status {row.update.status}
            </p>
            {row.update.correction_of ? (
              <p className="research-meta">
                Corrects an earlier copy of this official page. The earlier copy is kept.
              </p>
            ) : null}
            {variant === "evidence" ? (
              <dl className="research-meta mt-[var(--space-2)]">
                <div>
                  <dt>Source id</dt>
                  <dd>{row.update.source_id}</dd>
                </div>
                <div>
                  <dt>Retrieval id</dt>
                  <dd>{row.update.retrieval_id}</dd>
                </div>
                <div>
                  <dt>Content hash</dt>
                  <dd>{row.update.content_hash.slice(0, 16)}…</dd>
                </div>
                {row.update.correction_of ? (
                  <div>
                    <dt>Correction of</dt>
                    <dd>{row.update.correction_of}</dd>
                  </div>
                ) : null}
              </dl>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
