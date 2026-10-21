# AQIL — Research Crown Jewel: Evidence, Methods, Signals, Hypotheses and Learning
**Build intent:** An auditable research workflow that uses existing published methodologies before trying experimental AI extensions. No process may claim a predictive edge without prospective evidence.

**18 October 2026.** New macro-method work waits until it has a clear decision value for My Wealth or Deploy Capital. The November employment baseline remains a frozen prospective exercise. It is not evidence of forecasting skill.

## 1. Scientific chain of custody
Aqil's chain is `source → extract → verify → observation → event/indicator → causal candidate → applied named method → competing scenario → market-expectations check → eligible exposure analysis → registered forecast → paper experiment → independent evaluation → versioned learning`. Every arrow has a validator; any failing critical step stops publication or produces a visibly qualified research note.

### Distinguish five epistemic objects
- **Observed datum**: quoted or calculated from a specific source, with unit/period/definition; the source itself may be fallible.
- **Verified factual claim**: support is directly traceable to a permitted source span/structured record and checked for context; verified support **is not** proof the underlying source is correct.
- **Inference/causal hypothesis**: mechanism supported by assumptions and evidence; correlation must not be called causal proof.
- **Forecast/scenario**: contingent statement specifying probability *only if calibrated*, time horizon, observable target and falsification/evaluation rule.
- **Investment interpretation**: separate judgement about prices, investability, exposures and whether action improves a risk-constrained portfolio relative to status quo.

### Evidence levels and public display
- `official_primary`: authenticated regulatory/statistical/issuer source. May still be revised or wrong.
- `published_primary_research`: identifiable method/paper/data with caveats.
- `independent_reputable_secondary`: useful context and corroboration, distinguish syndicated copies.
- `discovery_only`: news/social lead requiring verification.
- `unverified`: quarantined; never used to assert consequential public facts or numbers.

Status lifecycle: `collected → parsed → corroboration_pending → verified_supported / contested / insufficient → candidate_thesis → reviewer_approved → published → corrected/superseded`. Unsupported claims never quietly pass into story prose; a summary may explicitly say evidence is insufficient.

**Critical correction to 'no hallucinations':** The capability specification is **zero tolerated unsupported consequential assertions at publish time**, not a promise of literally zero factual mistakes. LLM source attribution, source content and human review each can fail. Use layered controls, metrics and incident response.

## 2. Source verification contract
Every used claim requires `claim_id`, `claim_text`, `kind`, `source_artifact_id`, `source_span/field`, `source_published_at`, `retrieved_at`, `as_of`, `data_vintage`, `number_value/unit` where applicable, `verification_method`, `verification_result`, `reviewer`, `rights_class`, `retraction_status`, `freshness_class`.

Validation examples:
- A numeric fact extracted from an official CSV: recompute through deterministic parser with unit and timestamp check.
- A long-form primary policy document: show exact anchored text and section; human checks materially consequential wording (proposed vs enacted; appropriated vs spent).
- LLM-generated prose: require every material claim to reference a verified claim ID; check explicit subject, quantity, geography, date and modal ('may' vs 'will') consistency. Reject fabricated IDs and incompatible spans. A programmatic verifier can reduce but not guarantee prevention of unsupported entailment.
- Contradictory authoritative sources: label contested, list both and describe discrepancy; do not average claims into false certainty.
- Source correction/retraction: new source version and impact analysis; revise dependent research and publish linked correction if materially affected.

**Source independence:** Ten reports copying one press release = one origin; separate source count from story count. Backfill releases with true first-available time to avoid future knowledge in historical tests.

## 3. Methodology library: methodological humility
A method is eligible for use only after a `MethodCard` is created. Required fields: `method_id`, original citation/DOI, originator and year, research question, mathematical specification, underlying universe, horizon, historical data requirements, original study's execution rules, costs/FX/leverage/shorting, assumptions, known failure modes, regime boundaries, publication/reproduction evidence, licensing, implementation tests, point-in-time coverage, Aqil validation cohort, version hash, human approval, status.

**Status labels must never be conflated:**
1. `documented`: primary methodology documented (no claim we reproduced results).
2. `implemented`: deterministic code exists and passes unit tests (no predictive claim).
3. `replicated`: reproduce defined published outputs or independently specified acceptance fixture where available (does not prove future edge).
4. `historically_evaluated`: realistic point-in-time backtest, including failures and expenses.
5. `prospectively_testing`: frozen live-forward decisions under evaluation.
6. `prospectively_supported`: meets predeclared statistical/economic hurdles *for named cohort*; never blanket 'proven'.
7. `degraded/retired`: no longer useful or has failing integrity/rights.

### First-wave registry (not endorsements or verified 12/24/36-month alpha)
- Market-cap-weighted passive global equity baseline, rebalancing and diversification: core benchmark.
- Discounted cashflow/earnings-yield + valuation-based capital-market assumptions: longer-horizon framing; near-term timing weak.
- Fama-French value, profitability and investment factors: published systematic research; implementation exposures differ from broad UCITS ETFs.
- Industry/asset momentum and time-series trends: published historical effect; crash risk, costs, out-of-sample decay.
- Dynamic risk control/volatility and drawdown diagnostics: risk-management method, not guaranteed return enhancer.
- Regime classification for growth/inflation: useful for scenario framing; prediction of regimes hard.
- Covariance-based allocation, mean-variance and robust optimisation: documented mathematics, error-sensitive expected return inputs; use constraints and compare simple equal/risk allocation.
- Policy/event studies and supply–demand systems modelling: heterogeneity and endogeneity; not inherently return-predictive.
- Earnings revisions/consensus dispersion: potential information signal but costly historical point-in-time data.

Do **not** implement 20 methods in v1. Start with passive baseline, one risk diagnostic, one robust published quantitative signal (e.g. momentum, chosen only after data feasibility), and one event-to-causal research chain. All variants are preregistered.

### Historical analogues (later milestone; not M1)
Historical analogues and recurring market behaviour are a required later capability of this same method, factor, configuration and evidence architecture. They are not a separate product, not a universal scoring matrix, and not part of the first macro slice.

A future method card may compare a current episode with past macroeconomic, geopolitical and financial events; record how markets responded over short, medium and long horizons; and condition similarity on inflation, monetary policy, valuations, liquidity, expectations and other stated regime features. Historical price patterns, momentum, reversals and support or resistance may enter only as named, testable candidate factors with their own method cards. Similarity weights and thresholds are versioned configuration.

The method must show outcome distributions, contradictory precedents and patterns that failed. Inputs are point-in-time, so later revisions and later prices cannot leak into the comparison. Evaluation uses matched benchmarks, out-of-sample tests and explicit controls for overfitting. A historical correlation, a proposed causal explanation and a demonstrated predictive result stay separate objects. None of them is implied by the others.

### Modular research pipeline (M1)
The macro worker exposes small protocols, not a plugin platform:

- **Provider adapters** map provider-native fixtures or feeds to `observation.v1` only. Adapter choice is configuration (`adapter_id`). Disabling a source blocks new collection; it does not delete stored observations.
- **Analytical methods** consume a normalised as-of observation view. Method choice is configuration (`method_id` + versioned config hash). Replacing a provider or swapping methods does not change the orchestrator.
- **Configuration vs version:** parameter changes (thresholds, windows, labelled sensitivity cases) change `config_id` / `config_hash` only. Formula, input-contract or window-definition changes require a new `method_version`. A different research question requires a new `method_id` and MethodCard.
- **Future matrices:** methods may attach validated parameter documents (scalars and rectangular decimal matrices) via `MethodParameterDocument`; this is not a general factor-weighting engine.
- **ResearchRun** records a method **implementation hash** (for Sahm: SHA-256 of the `sahm.py` module bytes only—not transitive Python/runtime dependencies), **config hash**, **input snapshot hash** and a deterministic **analytical payload hash**. Publication remains a separate fail-closed gate from analytical completion.

### Eligibility recorded on 22 October 2026

The Sahm formula is unchanged: a 15-month window, a three-month average, and the minimum of the prior twelve three-month averages. October 2025 was not collected (BLS footnote 9, appropriations lapse). Every evaluation month from October 2025 through December 2026 includes that month and is permanently invalid. Nothing is interpolated. September 2025 can be a complete historical window, but it is not the current month. January 2027 is the next evaluation month that excludes October 2025. It becomes eligible only when November 2025 through January 2027 are all stored as real observations.

Census advance durable goods still compares the first stored vintage of the prior month with a later stored vintage. One current API response does not supply that pair, so the method stays insufficient until a later official release is stored as a new vintage. Historical vintages are not fabricated. A Census API key is still required before any request.

The SLOOS reading stays internal. `publication_allowed` remains false in the orchestrator. The Board file is the latest revised release, not a point-in-time panel. Claim and span verification are unverified. The method is not historically evaluated and has no human publication approval. Its investment implication is `no_action`. Counts of stored quarters are a position in that file, not a probability and not a forecast.

## 4. Signal detection: no autonomous conviction manufacture
- **Collectors:** official/public data feeds and rights-approved discovery sources; source-specific release schedule.
- **Normaliser:** entities, units, frequency, geography, geospatial/timeframe, published/available timestamps, revision, rights.
- **Detector:** explicit statistical thresholds, change-point methods if warranted, event/rule triggers or scheduled thesis review. Threshold versions logged.
- **Materiality:** size × economic exposure × persistence × evidence quality × portfolio relevance, with caps/limitations. This is an internal routing rule, not an invented probability of investment success.
- **Escalation:** expensive agent investigation only if materiality, unresolved ambiguity or new primary evidence justifies it. News volume by itself is not significance.
- **Deduplication:** cluster underlying original claim/event; identify reprints and copies; record contested observations.
- **No assumed direction:** catalysts can have beneficiaries, losers, unclear sign and feedback loops.

## 5. Causal pathway: pyramid research contract
1. **Global driver:** e.g. national electrification law, armed conflict, monsoon/yield anomaly, monetary policy.
2. **Transmission:** quantities, capacities, incentives, costs, substitution, geography, nonlinearity, lags and feedback.
3. **Sector and earnings consequence:** profit pools, margins, investment, discount rate, balance sheet, suppliers/competitors and losers.
4. **Expectations:** valuations, published analyst expectations/forward prices/implied rates if available, else 'pricing unknown'.
5. **Investable exposure:** likely ETF representation, geographic and sector look-through, competing drivers, liquidity, cost, history and overlap.
6. **No-action counterfactual:** hold and contribute to global index, rebalance if needed, do not force action.
7. **Registered, falsifiable investment forecast:** 12/24/36-month windows only when data supports meaningful test; may be `insufficient_evidence`.

Each directional graph edge stores `relation`, `mechanism`, `sign` (including unknown), `lag_range`, `geography`, `evidence_ids`, `confounders`, `substitution`, `status` and `version`; avoid false precision. Link confidence separately by observation quality, causal confidence and forecast calibration—not a single opaque percent.

### Country policy tracker
For each country/bloc, track proposal, bill, enactment, appropriations, appropriated vs disbursed funds, procurement, implementation, measurable uptake/output, enforcement, court challenge, reversal, trade response and foreign spillovers. Record effective dates and data revisions. Identify economic significance based on exposure, not merely country size.

### Example mini-contract: Middle East de-escalation (hypothetical; not a current prediction)
- Define precise geographical/event scope and outcome metric **before** evaluating claims.
- Signals: independent verified ceasefire compliance, cross-border kinetic incidents, military posture, shipping flows, insurance premia, physical oil exports, sanctions and policy follow-through. A diplomatic headline is not equivalent to confirmed operational de-escalation.
- Competing scenarios: durable de-escalation, temporary lull, renewed escalation; describe evidence and unknowns.
- Mechanisms: oil risk premia, maritime logistics, import costs, inflation, regional earnings and currency. Every edge can fail independently.
- Price check: forward curves, relevant equity valuations and countervailing global growth. Unknown market expectations → no claim of unpriced upside.
- Eligibility: existing global exposure, broad regional fund eligibility, risk constraints; most likely research output may be no change.
- Predeclare adjudication intervals and factual and financial tests. Track negative, profitable-accident and unresolved outcomes.

## 6. ETF eligibility and portfolio-context contracts
**Eligibility first:** official ISIN/share class, accumulating status, issuer/domicile, TER and tracking difference, index description/method, diversification/holdings, AUM/liquidity, fund risk/replication, historical fund/index performance labelled separately, asset/revenue geographic look-through, broker availability and restricted products. Trade currency is not underlying economic exposure. `CORE`, `CONDITIONAL`, `EXCLUDED`, `UNKNOWN`; missing hard evidence → `UNKNOWN`, never silently eligible.

**Attractiveness separate:** macro mechanism, valuation, earnings, time horizon, existing overlap, concentration and whether it improves risk/return expectations. A good instrument can be unattractive at current pricing. High past return does not prove good future prospects.

## 7. Register predictions before seeing results
`ForecastContract` freezes: exact target variable and units, population/event and region, observation window, due date, baseline, time horizon, probability (only if supportable and calibration method named), direction/range, source snapshot, method/prompt/model/code versions, expected economic consequences, portfolio experiment definition, fees/FX, evaluation rule, alternatives/falsifiers, author and timestamp.

Research can later update its beliefs **as a new forecast version**. The initial version remains accessible and evaluated. Don't label a scenario as a forecast unless its target and evaluation are well defined.

## 8. Shadow portfolio experiment design
**Three distinct comparison classes:** real-user portfolio (what happened to them), Aqil frozen shadow strategy (what the system recommended), flow-matched passive/rules-only controls (counterfactual). Never swap between them in reporting. No external user data required for virtual portfolio calculations; paper execution uses real public prices only if rights and corrections are reliable.

- Seed with preregistered benchmark, rules-only, frozen AI-informed and alternative scenario cohorts; no retrospective creation of the 'winning' strategy.
- All accounts use comparable initial capital, net cashflows, time zones, expected fills, splits, fees, liquidity and FX policies.
- Book simulated orders no earlier than *next actually executable* market opportunity with actual available data; missing/ambiguous quote blocks fill.
- Record selection biases, identical-factor exposure, look-through overlap, gross/net, absolute/relative risk, attribution and full unsuccessful strategy denominator.
- Treat 100 correlated paper accounts as many observations of decisions, **not 100 independent market histories**. Track effective sample size, overlapping windows, regimes and test multiplicity.
- Periodic scorecard: outcome by *event prediction*, *causal impact*, *instrument*, *whole portfolio* and *actual user behaviour*. A correct prediction with a losing ETF is not a success; a profitable incorrect forecast isn't predictive skill.

## 9. Learning system: improvement must shrink blast radius
- `Researcher` may explore hypotheses on exploratory data; cannot publish performance claims or alter champion logic.
- `Challenger` contains one declared methodological change, fixed objective/hurdle, previously untouched evaluation slice and documented comparisons.
- `Champion` is pinned to version and decisions for live-forward performance; upgrades are a formal version transition, not overwrite.
- `IndependentEvaluator` computes scores and can reject unsupported improvements; LLM post-mortem can suggest root causes but **may not assert causal certainty** without evidence.
- `Quarantine` immediately blocks contaminated providers/methods and propagates correction notices to linked hypotheses, stories, and evaluations; no reactive capital management.
- `Promotion`: only after correct tests, acceptable drawdown/turnover/data rights, economic significance, prospective window and human approval. Stage changes in shadow mode, then small user-facing rollout; never bypass strict approval for financial claims.
- `Rollback`: schema-compatible feature flags, release ledger, last known good method, alert and post-incident write-up.

**Blast-radius reduction metrics:** percent of claims blocked prepublication, downstream artifacts flagged/corrected within target, mean correction latency, maximum affected story count, stale-data detection latency, failed source isolation, invalid instrument prevention, number of unapproved production research changes (target zero).

## 10. Learning scorecards
- Probabilities: Brier score, reliability bins, base-rate comparison, sample size and confidence intervals; no made-up confidence badges.
- Numeric forecasts: absolute/scaled errors and baseline-relative improvement, units/horizon.
- Causal edge: whether the intermediate variables actually moved as forecast and whether competing drivers were considered; cautious attribution.
- Allocation: costs- and FX-adjusted excess return, TWR/MWR as appropriate, benchmark, risk, maximum drawdown, turnover and counterfactual.
- Method stability: by region, regime, vintage, cohort and time; false-discovery risks and research degrees of freedom.
- Research integrity: verified-support rate, source age, stale/blocked counts, retraction responsiveness and correction transparency.

## 11. Publication workflow
`agent_draft` never directly becomes `published`. Generation consumes **structured verified inputs**; citations are internal IDs, not fabricated URLs; rendered copy uses a claim-to-text linker. Numerical tables derive from computation not prose. A reviewer reads source spans and confirms nuanced conclusions, chronology, method applicability, legal/licensing. Publish only approved version; correction version has visible changelog. For low-stakes evergreen education, reviewed templates can be updated on a separately tested schedule.

## 12. What success and failure look like
Success may be 'Aqil showed convincingly that another 12-month allocation would have been needless; continuing a global ETF was sensible.' Success can also be 'It identified a genuine repeatable measurable strategy'. Failure is 'It produced a persuasive narrative without provenance or selectively celebrated paper winners'. No research decision is rewarded for being exciting.
