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
    description: "Current conditions, quantitative methods and what the evidence supports.",
  },
];

/** Intelligence section home. The release calendar stays on /calendar. */
export const intelligenceHome = "/conditions";

/**
 * Contextual navigation inside Intelligence.
 * The release calendar and the evidence record stay addressable.
 * They are not primary Intelligence sections.
 * ETF exposures stay on /explore and are outside this section.
 */
export const intelligenceNav: NavItem[] = [
  {
    href: "/conditions",
    label: "Dashboard",
    description: "Tracked observations, recent changes and upcoming releases.",
  },
  {
    href: "/intelligence/methodologies",
    label: "Methodologies",
    description: "Quantitative methods, their status and whether a result may be shown.",
  },
  {
    href: "/intelligence/insights",
    label: "Insights",
    description: "Findings that cite publication-eligible model results.",
  },
];

const intelligenceContextHrefs = ["/calendar", "/research"];

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
  return [...intelligenceHrefs, ...intelligenceContextHrefs].some((href) => matchesPath(pathname, href));
}

export function isPrimaryActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === intelligenceHome) return isIntelligencePath(pathname);
  return matchesPath(pathname, href);
}
