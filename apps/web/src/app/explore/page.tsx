import { Suspense } from "react";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import { EXPLORE_EMPTY_COPY } from "@/lib/research/present-sourced-updates";

function ExploreEmpty() {
  return (
    <div className="research-banner" data-testid="explore-empty">
      <p className="research-body">{EXPLORE_EMPTY_COPY}</p>
    </div>
  );
}

export default function ExplorePage() {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/explore">
          <Suspense fallback={<ExploreEmpty />}>
            <ExploreEmpty />
          </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
