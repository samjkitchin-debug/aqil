import { Suspense } from "react";

import { PrivatePage } from "@/components/auth/private-page";
import { AppShell } from "@/components/app-shell";
import { ResearchStoryView } from "@/components/research/research-story-view";

export default function DevStoryPage() {
  return (
    <AppShell title="Development">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/dev/story">
          <ResearchStoryView />
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
