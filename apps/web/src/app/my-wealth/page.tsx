import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { PrivatePage } from "@/components/auth/private-page";
import { PlaceholderPanel } from "@/components/placeholder-panel";

export default function MyWealthPage() {
  return (
    <AppShell title="My wealth">
      <Suspense fallback={<p className="text-muted">Checking your session…</p>}>
        <PrivatePage nextPath="/my-wealth">
          <div data-testid="wealth-empty">
            <PlaceholderPanel
              heading="My wealth"
              body="No holdings are recorded for this account. Portfolio figures appear only after you enter them while signed in. Demonstration fixtures are not shown here."
            />
          </div>
        </PrivatePage>
      </Suspense>
    </AppShell>
  );
}
