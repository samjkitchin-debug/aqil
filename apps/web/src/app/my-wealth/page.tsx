import { headers } from "next/headers";
import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { MyWealthView } from "@/components/wealth/my-wealth-view";
import { SAXO_SIM_REDIRECT_URI, saxoConnectAllowed } from "@/lib/saxo/sim-guard";
import { loadWealthSnapshot } from "@/lib/wealth/load-snapshot";

async function WealthBody({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const params = await searchParams;
  const load = await loadWealthSnapshot();
  const headerStore = await headers();
  const host = headerStore.get("x-forwarded-host") ?? headerStore.get("host") ?? "";
  const connectEnabled = saxoConnectAllowed({
    environment: "live",
    nodeEnv: process.env.NODE_ENV,
    requestHost: host,
    redirectUri: SAXO_SIM_REDIRECT_URI,
  });
  return (
    <PrivatePage nextPath="/my-wealth">
      <MyWealthView load={load} error={params.error ?? null} connectEnabled={connectEnabled} />
    </PrivatePage>
  );
}

export default function MyWealthPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  return (
    <AppShell title="My Wealth" showHeading={false}>
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <WealthBody searchParams={searchParams} />
      </Suspense>
    </AppShell>
  );
}
