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
  try {
    const file = await readJournalFile(access.userId);
    const summary = summariseJournal(file, safeQueryDate(params.asOf));
    return (
      <JournalPanel
        summary={summary}
        prices={file.prices}
        rates={file.rates}
        error={params.error ?? null}
        draftId={randomUUID()}
      />
    );
  } catch {
    return <p className="text-foreground">The journal could not be read.</p>;
  }
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
