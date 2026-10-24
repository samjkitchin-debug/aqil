import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { EtfExplorePanel } from "@/components/etf/etf-explore-panel";
import { StatusLine } from "@/components/ui/status-line";
import { loadEtfExplore } from "@/lib/etf/load-explore";
import {
  ETF_CITED_DOCUMENT_REQUIREMENT,
  ETF_EMPTY_COPY,
  ETF_RESEARCH_BOUNDARY,
  SHARE_CLASS_ABSENT,
} from "@/lib/etf/present-explore";

async function EtfExplore({ isin }: { isin?: string }) {
  const loaded = await loadEtfExplore(isin);

  if (loaded.status === "unavailable") {
    return (
      <div className="research-banner" data-testid="explore-unavailable">
        <h2 className="research-section-title">ETF research</h2>
        <p className="research-body">ETF research is unavailable. {loaded.reason}</p>
        <StatusLine tone="limitation">{ETF_RESEARCH_BOUNDARY}</StatusLine>
      </div>
    );
  }

  if (loaded.status === "absent") {
    return (
      <div className="research-banner" data-testid="explore-absent">
        <h2 className="research-section-title">ETF research</h2>
        <p className="research-body">{SHARE_CLASS_ABSENT}</p>
        <StatusLine tone="limitation">{ETF_RESEARCH_BOUNDARY}</StatusLine>
      </div>
    );
  }

  if (loaded.status === "empty") {
    return (
      <div className="research-banner" data-testid="explore-empty">
        <h2 className="research-section-title">ETF research</h2>
        <p className="research-body">{ETF_EMPTY_COPY}</p>
        <p className="research-body mt-[var(--space-4)]">{ETF_CITED_DOCUMENT_REQUIREMENT}</p>
        <StatusLine tone="limitation">{ETF_RESEARCH_BOUNDARY}</StatusLine>
      </div>
    );
  }

  return (
    <div data-testid="etf-explore">
      {loaded.shares.map((share) => (
        <EtfExplorePanel key={share.isin} share={share} />
      ))}
    </div>
  );
}

async function ExploreBody({
  searchParams,
}: {
  searchParams: Promise<{ isin?: string }>;
}) {
  const params = await searchParams;
  const isin = params.isin?.trim() || undefined;
  const nextPath = isin ? `/explore?isin=${encodeURIComponent(isin)}` : "/explore";
  return (
    <PrivatePage nextPath={nextPath}>
      <Suspense fallback={<p className="research-body">Loading ETF research…</p>}>
        <EtfExplore isin={isin} />
      </Suspense>
    </PrivatePage>
  );
}

export default function ExplorePage({
  searchParams,
}: {
  searchParams: Promise<{ isin?: string }>;
}) {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <ExploreBody searchParams={searchParams} />
      </Suspense>
    </AppShell>
  );
}
