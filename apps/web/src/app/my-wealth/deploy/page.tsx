import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { DeployCapitalPanel } from "@/components/capital/deploy-capital-panel";
import { readInvestmentPolicy } from "@/lib/capital/policy-file";
import { emptyInvestmentPolicy, formDefaultsFromStored } from "@/lib/capital/policy";
import { loadWealthSnapshot } from "@/lib/wealth/load-snapshot";
import { createSupabaseServerClient } from "@/lib/supabase/server";

async function DeployBody() {
  const load = await loadWealthSnapshot();
  const broker = load.status === "unauthorized" ? null : load.broker;
  const fx =
    load.status === "ok"
      ? load.snapshot.fx.map((rate) => ({
          baseCurrency: rate.baseCurrency,
          quoteCurrency: rate.quoteCurrency,
          rate: rate.rate,
        }))
      : [];
  const reportingCurrency =
    broker?.accounts.find((account) => account.currency)?.currency ??
    (load.status === "ok" ? load.snapshot.reportingCurrency : "SGD");
  const supabase = await createSupabaseServerClient();
  const { data: auth } = await supabase.auth.getUser();
  const policy = auth.user
    ? await readInvestmentPolicy(auth.user.id, reportingCurrency)
    : { runtime: emptyInvestmentPolicy(), form: formDefaultsFromStored(null) };
  return <DeployCapitalPanel broker={broker} fx={fx} policy={policy} />;
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
