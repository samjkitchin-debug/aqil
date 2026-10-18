import Link from "next/link";
import { Suspense } from "react";

import { IntelligenceNav } from "@/components/intelligence-nav";
import { PrimaryNav } from "@/components/primary-nav";
import { SiteFooter } from "@/components/site-footer";
import { SignOutControl } from "@/components/auth/sign-out-control";
import { PageContainer } from "@/components/ui/page-container";
import { SkipLink } from "@/components/ui/skip-link";
import { resolveAccess } from "@/lib/auth/access";

type AppShellProps = {
  title: string;
  children: React.ReactNode;
  /** Set false when the page already has its own h1, such as a legal document. */
  showHeading?: boolean;
};

async function SignedInAccount() {
  const access = await resolveAccess();
  if (access.status !== "authenticated_authorised") return null;
  return <SignOutControl />;
}

export function AppShell({ title, children, showHeading = true }: AppShellProps) {
  return (
    <div className="aq-shell">
      <SkipLink />
      <header className="aq-shell-header">
        <PageContainer>
          <div className="aq-header-bar">
            <Link href="/" prefetch={false} className="aq-brand-title">
              Aqil
            </Link>
            <PrimaryNav />
            <Suspense fallback={null}>
              <SignedInAccount />
            </Suspense>
          </div>
        </PageContainer>
      </header>

      <main className="aq-shell-main" id="main-content" tabIndex={-1}>
        <PageContainer>
          {showHeading ? (
            <h1 id="page-title" className="aq-page-title">
              {title}
            </h1>
          ) : null}
          <IntelligenceNav />
          {children}
          <SiteFooter />
        </PageContainer>
      </main>
    </div>
  );
}
