export type NavItem = {
  href: string;
  label: string;
  description: string;
};

export const primaryNav: NavItem[] = [
  {
    href: "/",
    label: "Today",
    description: "Your daily briefing placeholder.",
  },
  {
    href: "/explore",
    label: "Explore",
    description: "ETF exposure and holdings context.",
  },
  {
    href: "/calendar",
    label: "Calendar",
    description: "Upcoming catalysts for vetted ETFs.",
  },
  {
    href: "/my-wealth",
    label: "My wealth",
    description: "Portfolio and goals — not connected yet.",
  },
  {
    href: "/learn",
    label: "Learn",
    description: "Educational material will live here.",
  },
  {
    href: "/research",
    label: "Research",
    description: "Macro research engine output — not available yet.",
  },
];
