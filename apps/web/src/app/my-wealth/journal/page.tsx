import { randomUUID } from "node:crypto";
import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { JournalPanel } from "@/components/wealth/journal-panel";
import { resolveAccess } from "@/lib/auth/access";
import { readJournalFile } from "@/lib/wealth/journal-store";
import { safeQueryDate, summariseJournal } from "@/lib/wealth/journal-workflow";

async function JournalBody({
  searchParams,
}: {
  searchParams: Promise<{ asOf?: string; error?: string }>;
}) {
  const params = await searchParams;
  const access = await resolveAccess();
  if (access.status !== "authenticated_authorised") return null;
  let panel: {
    summary: ReturnType<typeof summariseJournal>;
    prices: Awaited<ReturnType<typeof readJournalFile>>["prices"];
    rates: Awaited<ReturnType<typeof readJournalFile>>["rates"];
  } | null = null;
  try {
    const file = await readJournalFile(access.userId);
    panel = {
      summary: summariseJournal(file, safeQueryDate(params.asOf)),
      prices: file.prices,
      rates: file.rates,
    };
  } catch {
    panel = null;
  }
  if (!panel) return <p className="text-foreground">The journal could not be read.</p>;
  return (
    <JournalPanel
      summary={panel.summary}
      prices={panel.prices}
      rates={panel.rates}
      error={params.error ?? null}
      draftId={randomUUID()}
    />
  );
}

export default function InvestmentJournalPage({
  searchParams,
}: {
  searchParams: Promise<{ asOf?: string; error?: string }>;
}) {
  return (
    <AppShell title="Investment journal">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/my-wealth/journal">
          <JournalBody searchParams={searchParams} />
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
