# AQIL — Human Experience, Editorial Design and Visual Manifesto
**Philosophy:** Design thinking is a repeating method, not a cosmetic treatment. Sophisticated research should be easy to approach and impossible to misrepresent through oversimplification.

## 1. The person comes before the dashboard
Every feature starts with a human problem and a comprehension test, not a proposed chart. Work, earn, support family, contribute when affordable, enjoy life and let time do useful work. Aqil removes analytical friction. It must not increase anxiety, FOMO, shame or checking compulsion.

Design for four broad, overlapping *use situations*, not patronising skill labels:
- **Five-minute commute:** 'Catch me up, connect the dots, tell me what remains unknown.'
- **First-ever ETF:** 'Explain the basics and give me realistic first steps without assuming I'm wealthy.'
- **Long-term portfolio owner:** 'Am I consistent, diversified and on track, without noise?' 
- **Analytical challenger:** 'Let me audit sources, quantitative methods, interpretations and failure history.'

Validate these with real user interviews. Interview at least novice, experienced investor and low-accessibility/low-confidence readers; recruit across a range of incomes and age groups without stereotyping. Test tasks and teach-back, not opinions about an attractive mockup.

## 2. Navigation
Implemented primary destinations are **Today**, **My Wealth** and **Intelligence**. Desktop places them in the sticky header. Narrow screens place the same three in one bottom bar. Intelligence keeps Upcoming (`/calendar`), Evidence (`/research`) and Exposures (`/explore`) as in-page links so a catalyst and its sources stay in one section. Learn remains available from the footer. Sign out sits in the header and is not grouped with education. An earlier six-item hypothesis (Today, Explore, Learn, My Wealth, Research, plus a separate calendar) is retired for the chrome: those jobs still exist, and their routes remain. Public legal pages require no login. Private portfolio and research pages do.

## 3. One knowledge object, three legitimate reading depths
The UI is a projection of **one approved versioned research object**, not three conflicting model answers:

**Quick read (45–90 seconds):** what changed, why relevant, what is uncertain, when updated and where to go next. Use prose; no unsupported confidence percentages.

**Connected analysis (4–6 minutes):** chain of causes, likely winners and losers, competing mechanisms, geography and horizon, optional accessible supporting chart, useful linked tangent(s). Tangents preserve breadcrumbs and 'return to original story'.

**Research detail (unlimited):** first-hand source links, dates/vintages, method cards, variables and assumption tables, causal links, scenarios, ETFs (when legitimately in scope), review trail, registered forecast and prospective outcomes including mistakes. Scary detail is opt-in, not hidden.

Material caveats and conflict-of-interest disclosures cannot be relegated solely to research detail.

## 4. Home/Today design contract
- Lead with a human-readable framing, one feature story, 3–5 meaningful developments, optional 'what we're still watching', one educational entry point. Quantity is editorially controlled, not automatically filled.
- Provide publication and update timestamps, genuine freshness, status (developing/verified/corrected), brief read length.
- Never auto-create investment advice from all global news. Useful 'no investment implications established' is allowed.
- Readability on phone: article first, charts after context, short paragraphs, anchored term definitions; no horizontal scroll for prose.
- No endless doomscroll, reaction counts, stock-price tickers by default, social trading or urgency badges.
- User can save stories and resume. Future optional daily brief notification should be opt-in, frequency limited and editorially useful.

## 5. Teach people investing without financial shame
Path: why saving matters → emergency buffer and high-interest debt → what ownership/markets mean → compounding (contributions versus growth) → diversification → ETFs (accumulating vs distributing) → volatility and time → fees and tax considerations → how to evaluate a broker → building and maintaining a plan.

**Interactive compounding laboratory:** start balance, periodic contributions, contributions increasing with earnings, assumed range of returns, inflation, fees, time horizon. Outputs separate nominal portfolio value, contributions and growth; show favourable/base/adverse scenarios and the risk of not meeting a date-specific goal. No prefilled guarantee, no implied universal 5% affordability.

**Goals:** child's education, house deposit, retirement, independence or custom. Make horizons explicit: a short-term essential goal is not the same as a 30-year discretionary retirement portfolio. Never imply equities cannot lose money.

## 6. My Wealth
First screen asks: 'How is my long-term plan progressing?' Then show contribution rhythm, invested holdings, value **as of** dated prices, benchmark, allocation and overlap, goals, data coverage and errors/unknowns.

The implemented page is an instrument panel. The headline is the standard account value when that figure is the one that matches cash plus holdings. Extended-hours value stays in account details, with its own basis. Open-position gain or loss is the sum of Saxo trade results in the account currency, labelled since the positions were opened, and is never described as today's return. Cash, the number of investments, the largest holding and the connection sit beside that headline. Composition is each holding's share of the standard account value, including cash when the total reconciles. An ETF stays one holding. A historical chart and a time-weighted return appear only when Saxo has actually returned them. The chart is account value, including contributions. It is not labelled investment return. A saved snapshot says when it was retrieved and does not claim a fresh connection. Positive and negative colours are for results, not for cash or ordinary amounts. Quantity, lots, prices, classification and source limits stay under details. Deploy capital is a separate read-only page. Saved Saxo cash can enter the calculation. Unclassified holdings are listed and are not assigned to an asset class. The example on that page is labelled as made up and is not the Saxo account.

Mandatory distinctions: deposits vs gains; nominal vs inflation-adjusted; realised vs unrealised; time-weighted vs money-weighted; public research vs personally executed trades; paper experiments vs actual portfolio. Missing FX or price -> transparent unavailable result, never made-up zero or interpolated value presented as fact. The current account value and the latest historical observation are different instants.

Avoid instant 'Buy/Sell' affordances. A portfolio-based research context can say: 'You already hold indirect exposure to this theme through global equities'; regulated personal recommendation boundary reviewed before public expansion.

## 7. The hardest screen: a wrong research outcome
Every important research outcome has `Original forecast`, `Evidence at the time`, `What actually happened`, `Which causal link failed`, `Portfolio consequence`, `What we still cannot tell`, `Method version and changes`, `Challenge this explanation`. A profitable accident is clearly labelled. Resolved outcomes are neither hidden nor celebrated by default; editorial design is neutral, not shaming or triumphant.

## 8. Visual manifesto
- **Predominantly white** like a calm long-horizon wealth/investor app, **not a trading terminal**. Original deep navy + warm gold inspired by Singapore Airlines' general aesthetic but not copying its logos, exact trade dress or implying affiliation.
- **Aptos-first** font stack. Use CSS fallbacks, do not bundle proprietary font without verifying rights.
- Meaningful whitespace, typography, soft dividers, disciplined information density, source-forward content.
- Reuse semantic colour, spacing, typography, border, radius, focus and chart tokens. **No hard-coded CSS/JSX colours** outside central tokens and documented exceptions.
- Gold is accent, not default body text. Test WCAG 2.2 AA foreground/background contrast; don't rely solely on colour to distinguish outcomes.
- Responsive first. Test 320px–430px mobile, tablet, desktop; charts have text equivalents, financial tables offer a mobile summary and explicit scroll when unavoidable.
- Support keyboard/screen reader, reduced motion, focus visibility, minimum touch comfort target 44x44 px where practical, readable 16px body, alt text, locale/currency preferences and accessible error explanations.
- Deliberately avoid excessive gradients, artificial glow, confetti, streaks, flashing gains, sensational red/green, FOMO notifications, decorative 3D graphics.

## 9. Component hierarchy
**Foundation components:** AppShell, Nav, Button, Link, Text, Heading, Card, SectionHeader, Badge (only meaningful state), Tabs, Accordion, Tooltip/GlossaryTerm, Empty/Loading/Error/Stale, DataTimestamp, Pagination, AccessibleTable, ChartFrame, FormField, Toast, Modal.

**Trust components:** SourceCitation (with supporting span/date), ClaimType, EvidenceStatus, CorrectionNotice, ResearchVersion, DataFreshness, MethodCard, UncertaintyExplanation, PeerChallenge, ForecastOutcome.

**Product components:** StoryCard, ConnectedPath, ScenarioComparison, GoalProjection, ContributionVsGrowth, ETFEligibility, HoldingsOverlap, PerformanceBreakdown, BenchmarkComparison, VirtualExperiment, OutcomePostmortem.

Each new component must justify itself rather than duplicate an existing pattern. UI does not perform its own investment calculations or generate claims.

## 10. Token discipline
`docs/design/tokens.css` is the design authority. `apps/web/src/styles/tokens.css` must stay aligned with it. Components use semantic tokens and the shared Tailwind aliases. Do not use raw `#hex`, `rgb()`, `hsl()`, or one-off spacing and radii in `apps/web/src` outside the token files. `npm run check:tokens` enforces that. New semantic needs amend the token files, not a page.

**How an execution session uses the design system:**
- Every page composes `AppShell` (`apps/web/src/components/app-shell.tsx`), which owns the header, brand, page title, footer, skip link and `PrimaryNav`. Do not copy a header or navigation into a page.
- Page files establish the route, load data through a server module, and compose feature components inside `PrivatePage` when the route is signed-in.
- Feature presentation lives in `apps/web/src/components/<feature>/`. Shared layout primitives live in `components/ui/`.
- Copy is UK English and sentence case. Empty, loading and unavailable states say what is missing. They do not invent figures.
- Local component CSS may set layout, and it must consume tokens such as `var(--space-3)` and `text-muted`.

## 11. User-research and design thinking cycles
**Discover:** 8–12 qualitative conversations across experience levels (initial target), capture jobs and confusion points. **Define:** problem statement, observable success/failure and prohibited implications. **Sketch:** low fidelity before polished screens. **Prototype:** same story at three depth levels, one investment lesson, one portfolio snapshot with missing data, one failed forecast. **Test:** tasks and teach-back, accessibility walkthrough, what people *misunderstood*. **Refine:** adjust navigation/content system, not core epistemic facts; repeat.

Prototype acceptance exercises:
1. After 60 seconds, reader explains central claim and one critical uncertainty accurately.
2. Novice can find and understand contribution-vs-return distinction.
3. Expert can locate underlying observation, method and a contradicting source in ≤3 deliberate steps.
4. User sees dated correction where original research was published.
5. Users don't assume a hypothetical portfolio is their actual result.
6. Article with absent market-data source still clearly conveys meaningful uncertainty and **does not** generate an unsupported ETF recommendation.

## 12. What design must not optimise
Clicks on ticker links, research volume, forecast frequency, screen time, social outrage, news addiction, account-value checking and referral conversion at the expense of readers' interests. User leaves informed and calm: successful session.
