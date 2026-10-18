import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { MyWealthView } from "@/components/wealth/my-wealth-view";
import { loadWealthSnapshot } from "@/lib/wealth/load-snapshot";

async function WealthBody({ error }: { error: string | null }) {
  const load = await loadWealthSnapshot();
  return (
    <PrivatePage nextPath="/my-wealth">
      <MyWealthView load={load} error={error} />
    </PrivatePage>
  );
}

export default async function MyWealthPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const params = await searchParams;
  return (
    <AppShell title="My wealth">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <WealthBody error={params.error ?? null} />
      </Suspense>
    </AppShell>
  );
}
