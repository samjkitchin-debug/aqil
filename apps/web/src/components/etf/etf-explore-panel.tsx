import Link from "next/link";

import { StatusLine } from "@/components/ui/status-line";
import { mapCitedExposure } from "@/lib/etf/exposure-context";
import {
  ETF_RESEARCH_BOUNDARY,
  EXPOSURES_ABSENT,
  assessmentCopy,
  benchmarkCopy,
  costsCopy,
  exposureCopy,
  freshnessCopy,
  holdingsCopy,
  identityCopy,
  listingsCopy,
  returnsCopy,
  structureCopy,
  type EtfShareExplore,
} from "@/lib/etf/present-explore";

type Props = {
  share: EtfShareExplore;
};

export function EtfExplorePanel({ share }: Props) {
  return (
    <article className="research-banner" data-testid="etf-share-class">
      <h2 className="research-section-title">Share class</h2>
      <p className="research-body">{identityCopy(share)}</p>
      <p className="research-body">{structureCopy(share)}</p>
      <h3 className="research-section-title">Listings</h3>
      <p className="research-body">{listingsCopy(share)}</p>
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
      <h3 className="research-section-title">Benchmark</h3>
      <p className="research-body">{benchmarkCopy(share)}</p>
      <p className="research-body">{returnsCopy(share)}</p>
      <h3 className="research-section-title">Assessment</h3>
      <p className="research-body">{assessmentCopy(share)}</p>
      <StatusLine tone="limitation">{ETF_RESEARCH_BOUNDARY}</StatusLine>
    </article>
  );
}
