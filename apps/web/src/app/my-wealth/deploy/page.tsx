import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { DeployCapitalPanel } from "@/components/capital/deploy-capital-panel";

export default function DeployCapitalPage() {
  return (
    <AppShell title="Deploy capital" showHeading={false}>
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/my-wealth/deploy">
          <DeployCapitalPanel />
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
