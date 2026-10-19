import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { CompoundingIllustration } from "@/components/learn/compounding-illustration";
import { ReadingContainer } from "@/components/ui/reading-container";

export default function LearnPage() {
  return (
    <AppShell title="Learn">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/learn">
          <ReadingContainer>
            <CompoundingIllustration />
          </ReadingContainer>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
