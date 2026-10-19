import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { DeployCapitalPanel } from "@/components/capital/deploy-capital-panel";
import { loadWealthSnapshot } from "@/lib/wealth/load-snapshot";
import type { Target } from "@/lib/wealth/allocation";

async function DeployBody() {
  const load = await loadWealthSnapshot();
  const broker = load.status === "unauthorized" ? null : load.broker;
  const targets: Target[] | null =
    load.status === "ok"
      ? load.snapshot.targets.filter((target): target is Target => target.assetClass !== "emergency_reserve")
      : null;
  const fx =
    load.status === "ok"
      ? load.snapshot.fx.map((rate) => ({
          baseCurrency: rate.baseCurrency,
          quoteCurrency: rate.quoteCurrency,
          rate: rate.rate,
        }))
      : [];
  return <DeployCapitalPanel broker={broker} targets={targets && targets.length > 0 ? targets : null} fx={fx} />;
}

export default function DeployCapitalPage() {
  return (
    <AppShell title="Deploy capital" showHeading={false}>
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/my-wealth/deploy">
          <DeployBody />
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
