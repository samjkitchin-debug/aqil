import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { PlaceholderPanel } from "@/components/placeholder-panel";

export default function LearnPage() {
  return (
    <AppShell title="Learn">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/learn">
          <PlaceholderPanel body="Structured learning paths on macro research, risk and disciplined long-horizon investing will be added with product documentation." />
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
