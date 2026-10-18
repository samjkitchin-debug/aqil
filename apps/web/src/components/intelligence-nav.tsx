"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { intelligenceNav, isIntelligencePath, matchesPath } from "@/lib/navigation";

export function IntelligenceNav() {
  const pathname = usePathname();
  if (!isIntelligencePath(pathname)) return null;

  return (
    <nav aria-label="Intelligence" className="aq-section-nav">
      <ul className="aq-section-list">
        {intelligenceNav.map((item) => {
          const active = matchesPath(pathname, item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                prefetch={false}
                className={active ? "aq-section-link aq-section-link--active" : "aq-section-link"}
                aria-current={active ? "page" : undefined}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
