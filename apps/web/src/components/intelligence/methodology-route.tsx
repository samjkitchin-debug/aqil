import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { MethodologyDetail } from "@/components/intelligence/methodology-detail";

export function MethodologyRoute({ slug }: { slug: string }) {
  return (
    <AppShell title="Intelligence">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath={`/intelligence/methodologies/${slug}`}>
          <Suspense fallback={<p className="research-body">Loading methodology…</p>}>
            <MethodologyDetail slug={slug} />
          </Suspense>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
