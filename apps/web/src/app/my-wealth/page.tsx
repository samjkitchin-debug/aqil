import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { MyWealthView } from "@/components/wealth/my-wealth-view";
import { loadWealthSnapshot } from "@/lib/wealth/load-snapshot";
import { toWire } from "@/lib/wealth/serialize";

async function MyWealthDetail() {
  const loaded = await loadWealthSnapshot();

  if (loaded.status === "unauthorized") {
    return (
      <p className="wealth-body">
        My wealth is available to the founder session. Sign in with Supabase Auth to persist your
        own portfolio, or enable the founder insight gate in non-production environments.
      </p>
    );
  }

  if (loaded.status === "empty") {
    return (
      <p className="wealth-body">
        No portfolio data is stored for this account yet. Import or enter positions once seeding
        tools are connected to your authenticated user.
      </p>
    );
  }

  return <MyWealthView snapshot={toWire(loaded.snapshot)} />;
}

function MyWealthFallback() {
  return <p className="wealth-body">Loading your portfolio…</p>;
}

export default function MyWealthPage() {
  return (
    <AppShell title="My wealth">
      <Suspense fallback={<MyWealthFallback />}>
        <MyWealthDetail />
      </Suspense>
    </AppShell>
  );
}
