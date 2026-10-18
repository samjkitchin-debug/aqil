"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { isPrimaryActive, primaryNav } from "@/lib/navigation";

export function PrimaryNav() {
  const pathname = usePathname();
  const [keyboardOpen, setKeyboardOpen] = useState(false);

  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return;

    const onResize = () => {
      const obscured = window.innerHeight - viewport.height;
      setKeyboardOpen(obscured > 120);
    };

    onResize();
    viewport.addEventListener("resize", onResize);
    return () => viewport.removeEventListener("resize", onResize);
  }, []);

  return (
    <nav
      aria-label="Primary"
      className={keyboardOpen ? "aq-primary aq-primary--keyboard" : "aq-primary"}
    >
      <ul className="aq-nav-list">
        {primaryNav.map((item) => {
          const active = isPrimaryActive(pathname, item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                prefetch={false}
                className={active ? "aq-nav-link aq-nav-link--active" : "aq-nav-link"}
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
