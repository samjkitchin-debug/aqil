"use client";

import { useState } from "react";

import type {
  ResearchSourceCitation,
  ResearchStoryDepthKey,
  SyntheticResearchStoryV1,
} from "@/lib/research/story";
import { lookupSources } from "@/lib/research/story";

const DEPTH_LABELS: Record<ResearchStoryDepthKey, string> = {
  quick_read: "Quick read",
  connected_analysis: "Connected",
  research_detail: "Full research",
};

type Props = {
  story: SyntheticResearchStoryV1;
};

function CitationList({ citations }: { citations: ResearchSourceCitation[] }) {
  return (
    <ul className="forward-horizon-list" data-testid="research-story-citations">
      {citations.map((row) => (
        <li key={row.source_id} className="research-meta">
          <a href={row.primary_url} rel="noopener noreferrer">
            {row.title}
          </a>
          {" · "}
          Source time {row.observed_at} · {row.source_id}
        </li>
      ))}
    </ul>
  );
}

export function ResearchStoryDepthPanel({ story }: Props) {
  const [depth, setDepth] = useState<ResearchStoryDepthKey>("quick_read");
  const citations = lookupSources(story, story.quick_read.source_ids);

  return (
    <section data-testid="research-synthetic-story">
      <div className="research-banner research-banner--preview">
        <StatusBanner label={story.label} />
        <p className="research-meta" data-testid="research-story-status">
          Status {story.status.replaceAll("_", " ")} · Research version {story.research_version_id}{" "}
          · Updated {story.updated_at}
        </p>
        <nav aria-label="Research depth" className="research-meta">
          {(Object.keys(DEPTH_LABELS) as ResearchStoryDepthKey[]).map((key) => (
            <button
              key={key}
              type="button"
              className="aq-button"
              aria-pressed={depth === key}
              data-testid={`research-depth-${key}`}
              onClick={() => setDepth(key)}
              style={{ marginRight: "var(--space-2)", marginTop: "var(--space-2)" }}
            >
              {DEPTH_LABELS[key]}
            </button>
          ))}
        </nav>
      </div>

      {depth === "quick_read" && (
        <article data-testid="research-depth-content-quick_read">
          <h2 className="research-headline">{story.quick_read.headline}</h2>
          <p className="research-body">{story.quick_read.summary}</p>
          <h3 className="research-section-title">Material uncertainty</h3>
          <p className="research-body">{story.quick_read.material_uncertainty}</p>
        </article>
      )}

      {depth === "connected_analysis" && (
        <article data-testid="research-depth-content-connected_analysis">
          <h2 className="research-section-title">Connected analysis</h2>
          <p className="research-body">{story.connected_analysis.body}</p>
          <h3 className="research-section-title">Causal links (illustrative)</h3>
          <ul className="forward-horizon-list">
            {story.connected_analysis.causal_links.map((link) => (
              <li key={link} className="research-body">
                {link}
              </li>
            ))}
          </ul>
        </article>
      )}

      {depth === "research_detail" && (
        <article data-testid="research-depth-content-research_detail">
          <h2 className="research-section-title">Method and audit</h2>
          <p className="research-body">{story.research_detail.method_summary}</p>
          <p className="research-body">{story.research_detail.audit_notes}</p>
          {story.research_detail.insufficient_evidence && (
            <p className="research-meta" data-testid="research-insufficient-evidence">
              Insufficient evidence for publication.
            </p>
          )}
        </article>
      )}

      <h3 className="research-section-title">Sources</h3>
      <CitationList citations={citations} />

      <div data-testid="research-story-correction">
        <h3 className="research-section-title">Correction</h3>
        <p className="research-body">{story.correction.summary}</p>
        <p className="research-meta">
          {story.correction.correction_id} · Corrected {story.correction.corrected_at} · Supersedes{" "}
          {story.correction.supersedes_research_version_id}
        </p>
      </div>
    </section>
  );
}

function StatusBanner({ label }: { label: string }) {
  return (
    <p className="research-meta" data-testid="research-synthetic-label">
      {label}
    </p>
  );
}
