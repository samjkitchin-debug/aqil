import Link from "next/link";

import { StatusLine } from "@/components/ui/status-line";
import { mapCitedExposure } from "@/lib/etf/exposure-context";
import {
  ETF_RESEARCH_BOUNDARY,
  EXPOSURES_ABSENT,
  approvalCopy,
  assessmentCopy,
  benchmarkCopy,
  costsCopy,
  eligibilityDecisionCopy,
  exposureCopy,
  freshnessCopy,
  holdingsCopy,
  identityCopy,
  listingsCopy,
  navCopy,
  priceCopy,
  quoteCopy,
  returnsCopy,
  structureCopy,
  FX_GAP,
  OVERLAP_UNAVAILABLE,
  PERFORMANCE_SEPARATE,
  type EtfShareExplore,
} from "@/lib/etf/present-explore";

type Props = {
  share: EtfShareExplore;
};

export function EtfUniverseFilter({ isin }: { isin?: string }) {
  return (
    <form
      className="research-banner"
      method="get"
      action="/explore"
      data-testid="etf-universe-filter"
    >
      <h2 className="research-section-title">Universe</h2>
      <label className="research-body" htmlFor="etf-isin">
        ISIN
      </label>
      <input
        id="etf-isin"
        name="isin"
        defaultValue={isin ?? ""}
        autoComplete="off"
        className="mt-[var(--space-1)] block w-full max-w-xs border border-border bg-surface p-[var(--space-2)]"
      />
      <button type="submit" className="aq-button mt-[var(--space-3)]">
        Show share class
      </button>
      <p className="research-meta">
        A ticker is not an identity. This page does not place an order.
      </p>
    </form>
  );
}

export function EtfExplorePanel({ share }: Props) {
  return (
    <article className="research-banner" data-testid="etf-share-class">
      <h2 className="research-section-title">Share class</h2>
      <p className="research-body">{identityCopy(share)}</p>
      <p className="research-body">{structureCopy(share)}</p>
      <h3 className="research-section-title">Listings</h3>
      <p className="research-body">{listingsCopy(share)}</p>
      <h3 className="research-section-title">Price and freshness</h3>
      <p className="research-body" data-testid="etf-price">
        {priceCopy(share)}
      </p>
      <p className="research-body">{navCopy(share)}</p>
      <p className="research-body">{quoteCopy(share)}</p>
      <h3 className="research-section-title">Cited costs</h3>
      <p className="research-body">{costsCopy(share)}</p>
      <h3 className="research-section-title">Evidence freshness</h3>
      <p className="research-meta">{freshnessCopy(share)}</p>
      <h3 className="research-section-title">Cited exposures</h3>
      {share.exposures.length === 0 ? (
        <p className="research-body" data-testid="cited-exposures-absent">
          {EXPOSURES_ABSENT}
        </p>
      ) : (
        <div data-testid="cited-exposures">
          {share.exposures.map((exposure) => {
            const context = mapCitedExposure(exposure.exposureClass);
            return (
              <div key={`${exposure.exposureClass}-${exposure.asOf}-${exposure.sourceId}`}>
                <p className="research-body">{exposureCopy(exposure)}</p>
                {context.status === "missing" ? (
                  <p className="research-body">{context.sentence}</p>
                ) : (
                  <>
                    <p className="research-body">{context.contextSentence}</p>
                    <ul>
                      {context.series.map((series) => (
                        <li key={series.sourceId}>
                          <Link className="aq-quiet-link" href={series.href}>
                            {series.name}
                          </Link>
                        </li>
                      ))}
                    </ul>
                    {context.unitedStatesReading ? (
                      <p className="research-body">
                        <Link className="aq-quiet-link" href={context.unitedStatesReading.href}>
                          {context.unitedStatesReading.heading}
                        </Link>
                        . {context.unitedStatesReading.sentence}
                      </p>
                    ) : null}
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
      <h3 className="research-section-title">Holdings</h3>
      <p className="research-body">{holdingsCopy(share)}</p>
      <h3 className="research-section-title">Overlap</h3>
      <p className="research-body" data-testid="etf-overlap">
        {share.overlapReason || OVERLAP_UNAVAILABLE}
      </p>
      <h3 className="research-section-title">Benchmark</h3>
      <p className="research-body">{benchmarkCopy(share)}</p>
      <p className="research-body">{returnsCopy(share)}</p>
      <h3 className="research-section-title">Performance</h3>
      <p className="research-body">{PERFORMANCE_SEPARATE}</p>
      <h3 className="research-section-title">Sources</h3>
      <p className="research-body">{share.fxSentence || FX_GAP}</p>
      <h3 className="research-section-title">Eligibility</h3>
      <p className="research-body">{eligibilityDecisionCopy(share)}</p>
      <h3 className="research-section-title">Assessment</h3>
      <p className="research-body">{assessmentCopy(share)}</p>
      <h3 className="research-section-title">Approval history</h3>
      <p className="research-body" data-testid="etf-approval">
        {approvalCopy(share)}
      </p>
      <StatusLine tone="limitation">{ETF_RESEARCH_BOUNDARY}</StatusLine>
    </article>
  );
}
