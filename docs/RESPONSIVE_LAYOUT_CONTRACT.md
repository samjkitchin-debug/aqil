# Responsive layout contract (G0)

**Status:** foundation for installable PWA and responsive web. Not final visual design.

## Authority

- Colour, type and spacing tokens: `docs/design/tokens.css` (mirrored in `apps/web/src/styles/tokens.css`).
- Shell layout utilities: `apps/web/src/styles/layout.css` (semantic classes only; no new colours).
- Primitives: `PageContainer`, `ReadingContainer`, `SkipLink` under `apps/web/src/components/ui/`.

## Layout tokens

| Token | Purpose |
|-------|---------|
| `--layout-content-max-width` | App content column (`--width-app`) |
| `--layout-reading-max-width` | Prose / story reading measure (`--width-reading`) |
| `--layout-gutter` | Horizontal page padding (scales at 390px, 768px, 1440px+) |
| `--layout-section-gap` | Main vertical rhythm between sections |
| `--layout-header-height` | Header bar minimum height |
| `--layout-nav-height` | Mobile bottom navigation row height |
| `--layout-touch-target-min` | Minimum interactive target (44px) |
| `--layout-safe-*` | `safe-area-inset` for installed PWAs |

Gutters and section gap increase at **390px**, **768px**, **1024px** (via `--layout-section-gap` at 64rem), and **1440px+** (90rem gutter). One layout adapts; we do not ship separate mobile/desktop apps.

## Test viewport targets

Use in Playwright and manual QA (not separate layouts):

| Target | Width | Typical use |
|--------|-------|-------------|
| Small phone | 320px | Overflow, nav fit, minimum readable body |
| Large phone | 390–480px | Primary mobile PWA |
| Tablet | 768px | Gutters, primary navigation moves into the header |
| Laptop | 1024–1440px | Desktop reading width |
| Large desktop | 1920px+ | Max-width centring |

## Shell behaviour

- **Narrow screens (under `48rem`):** sticky header with the wordmark and, when signed in, Sign out. The same three primary links (Today, My Wealth, Intelligence) are a fixed one-row bar at the bottom, with safe-area padding. The shell is at least `100dvh`, and main content is padded so the bar does not cover the footer. The bar hides while the on-screen keyboard obscures the visual viewport. Labels do not ellipsise.
- **Tablet and up (`48rem`):** those three links sit in the sticky header. There is no bottom bar and no navigation after the footer.
- **Intelligence routes** (`/calendar`, `/research`, `/explore`) add a section nav under the page title: Upcoming, Evidence, Exposures.
- **One page title.** `AppShell` renders the `h1` unless `showHeading` is false because the page already has one (legal documents, My wealth).
- **No horizontal overflow** on shell routes; layout must size correctly at 320px without relying on `overflow-x: clip` to hide content.
- **Skip link** to `#main-content`; visible on keyboard focus.
- **Touch:** primary links, Sign out and the primary button meet `--layout-touch-target-min`.
- **Zoom / text scaling:** relative units and `rem` tokens; no fixed pixel typography in components.

## PWA

- Manifest: `scope` `/`, `display_override` standalone; **no service worker** and **no offline cache** of authenticated portfolio or financial data in this gate.
- Viewport: `viewportFit: cover` with safe-area tokens on shell chrome.

## Automated checks (not full a11y sign-off)

- Playwright: overflow, routes, nav visibility, keyboard focus path, responsive projects.
- axe-core: smoke scan on key pages; violations fail CI. Manual screen reader and WCAG review remain required per `docs/05_HUMAN_EXPERIENCE_AND_DESIGN.md`.

## Out of scope (this contract)

Final Today/Research layouts, charts, data tables, offline mode, and My Wealth dashboards.
