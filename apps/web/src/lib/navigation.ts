export type NavItem = {
  href: string;
  label: string;
  description: string;
};

/** Destinations that stay visible on desktop and mobile. */
export const primaryNav: NavItem[] = [
  {
    href: "/",
    label: "Today",
    description: "What matters, what changed and what needs attention.",
  },
  {
    href: "/my-wealth",
    label: "My Wealth",
    description: "Holdings, allocation, targets and data completeness.",
  },
  {
    href: "/conditions",
    label: "Intelligence",
    description: "Tracked indicators, their state and freshness.",
  },
];

/** Intelligence section home. Upcoming stays on /calendar. */
export const intelligenceHome = "/conditions";

/**
 * Contextual navigation inside Intelligence.
 * Routes stay addressable; they are not extra primary destinations.
 */
export const intelligenceNav: NavItem[] = [
  {
    href: "/conditions",
    label: "Conditions",
    description: "Tracked indicators, trends and freshness.",
  },
  {
    href: "/calendar",
    label: "Upcoming",
    description: "Scheduled economic catalysts.",
  },
  {
    href: "/research",
    label: "Evidence",
    description: "Observations, scenarios, sources and outcome review.",
  },
  {
    href: "/explore",
    label: "Exposures",
    description: "Vetted ETF look-through. Not a separate product area.",
  },
];

/** Occasional literacy. Not an account control and not a daily destination. */
export const learnLink: NavItem = {
  href: "/learn",
  label: "Learn",
  description: "Explanations of unfamiliar investing and research terms.",
};

const intelligenceHrefs = intelligenceNav.map((item) => item.href);

export function matchesPath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function isIntelligencePath(pathname: string): boolean {
  return intelligenceHrefs.some((href) => matchesPath(pathname, href));
}

export function isPrimaryActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === intelligenceHome) return isIntelligencePath(pathname);
  return matchesPath(pathname, href);
}
