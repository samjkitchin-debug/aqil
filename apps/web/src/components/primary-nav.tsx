"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PageContainer } from "@/components/ui/page-container";
import { primaryNav } from "@/lib/navigation";

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function PrimaryNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="border-t border-border bg-surface shadow-card md:border-b md:border-t-0">
      <PageContainer>
        <ul className="aq-nav-list items-stretch py-[var(--space-1)] md:flex md:justify-start md:gap-[var(--space-2)]">
          {primaryNav.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <li key={item.href} className="min-w-0 md:flex-none">
                <Link
                  href={item.href}
                  className={[
                    "aq-nav-link",
                    active ? "aq-nav-link--active" : "aq-nav-link--idle",
                  ].join(" ")}
                  aria-current={active ? "page" : undefined}
                >
                  <span className="truncate">{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </PageContainer>
    </nav>
  );
}
