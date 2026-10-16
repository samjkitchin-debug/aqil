import Link from "next/link";

import { PrimaryNav } from "@/components/primary-nav";
import { PageContainer } from "@/components/ui/page-container";
import { SkipLink } from "@/components/ui/skip-link";

type AppShellProps = {
  title: string;
  children: React.ReactNode;
};

export function AppShell({ title, children }: AppShellProps) {
  return (
    <div className="aq-shell">
      <SkipLink />
      <header className="aq-shell-header">
        <PageContainer>
          <div className="flex min-h-[var(--layout-header-height)] items-center justify-between gap-[var(--space-3)]">
            <Link
              href="/"
              className="aq-brand-title text-brand-navy font-semibold tracking-tight"
            >
              Aqil
            </Link>
            <p className="aq-shell-page-title hidden text-muted sm:block">
              {title}
            </p>
          </div>
        </PageContainer>
      </header>

      <main className="aq-shell-main" id="main-content" tabIndex={-1}>
        <PageContainer>{children}</PageContainer>
      </main>

      <div className="aq-shell-nav-host">
        <PrimaryNav />
      </div>
    </div>
  );
}
