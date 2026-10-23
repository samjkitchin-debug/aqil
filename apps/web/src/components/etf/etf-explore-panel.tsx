import { StatusLine } from "@/components/ui/status-line";
import {
  ETF_RESEARCH_BOUNDARY,
  assessmentCopy,
  benchmarkCopy,
  costsCopy,
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
