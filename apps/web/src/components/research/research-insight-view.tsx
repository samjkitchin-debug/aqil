import Link from "next/link";

import { UnemploymentSparkline } from "@/components/research/unemployment-sparkline";
import type { ResearchInsightV1 } from "@/lib/research/types";

type Props = {
  insight: ResearchInsightV1;
  source: "local" | "fixture";
  compact?: boolean;
};

export function ResearchInsightView({ insight, source, compact = false }: Props) {
  const isPreview = insight.publication_status !== "not_eligible";
  const bannerLabel =
    source === "fixture"
      ? "Demonstration data (fixture)"
      : isPreview
        ? "Internal research preview — not publicly verified"
        : "Research insight";

  return (
    <article data-testid="research-insight">
      <div
        className={`research-banner${isPreview ? " research-banner--preview" : ""}`}
        data-testid="research-preview-banner"
      >
        <p className="research-meta">{bannerLabel}</p>
        <h2 className="research-headline">{insight.headline}</h2>
        {!compact && (
          <p className="research-body">{insight.what_changed}</p>
        )}
      </div>

      {!compact && (
        <>
          <UnemploymentSparkline
            points={insight.chart_points ?? []}
            label="US seasonally adjusted unemployment rate"
          />

          <h3 className="research-section-title">Why it matters</h3>
          <p className="research-body">{insight.why_it_matters}</p>

          <h3 className="research-section-title">Historical context</h3>
          <p className="research-body">{insight.historical_context}</p>

          <h3 className="research-section-title">Investor implications</h3>
          <p className="research-body">{insight.investor_implications}</p>

          <h3 className="research-section-title">Confidence and limitations</h3>
          <p className="research-body">{insight.confidence_and_limitations}</p>

          <h3 className="research-section-title">What comes next?</h3>
          <p className="research-body">{insight.what_comes_next}</p>

          <h3 className="research-section-title">Evidence</h3>
          <p className="research-body">{insight.source_attribution}</p>
          <p className="research-meta" data-testid="research-run-ref">
            Run {insight.run_id} · verification {insight.verification_status} ·
            hash {insight.analytical_payload_hash?.slice(0, 12) ?? "n/a"}…
          </p>
        </>
      )}

      {compact && (
        <p className="research-meta">
          <Link href="/research">View full research</Link>
        </p>
      )}
    </article>
  );
}
