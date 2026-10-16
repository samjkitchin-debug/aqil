# AQIL — Execution Roadmap and Stage Gates

## Strategic order
**Do not confuse feature completeness with research reliability.** Two tracks run in parallel: a small human-facing prototype to validate comprehension, and deep evidence/accounting infrastructure to validate correctness. Only combine them in a live research journey after gates pass.

| Gate | Objective | Hard evidence to proceed | Explicitly deferred |
|---|---|---|---|
| G0: Ground truth and feasibility | Verify data access/rights and trusted repo foundation | UCITS instrument/price/FX sample, primary macro source with a revision, rights matrix, CI/RLS, token UI prototype | mass feeds, agents, prices, public launch |
| G1: Human understanding prototype | Test Today/Explore/Learn/Research presentation | Novices and experienced readers can explain same sample analysis and its uncertainties; mobile/a11y tests | investment signal automation |
| G2: Portfolio truth | Build manual account journal + deterministic benchmark | Reproducible multi-currency ledger, total return/flows, error states, XIRR/TWR limitations, two-tenant isolation | broker integrations |
| G3: Method foundation | Implement and reproduce baseline model(s) | documented method cards, verified dataset, named equations/assumptions, transparent benchmark | multiple agents |
| G4: One research causal pathway | Take one official event through end-to-end publication | verified claims, opposing interpretation, methodology results, human approval, layered story, frozen forecast | 30-domain live ingestion |
| G5: Laboratory and learning | Evaluate prospective paper outcomes and errors | frozen control/variant accounts, valid simulated execution, predetermined adjudication, corrections, challenger process | claims of proven alpha |
| G6: Private reliable service | Run as founder's daily tool and correct failures | backup restore, source outage handling, manageable spend, genuine personal utility | personalised public recommendations |
| G7: Public free multi-user | Add safe anonymous reading/accounts/peer challenge | privacy/rights/legal review, tenant isolation, moderation, accessibility and scale | subscriptions |
| G8: Subscription-readiness | Honor founder free cohort and paid entitlement | tested cutoff terms, anti-abuse, billing/security/legal, provider rights, cost viability | trade execution |

## First three pull requests
**PR1: Repository and truth primitives.** Next.js app skeleton and tokens, Supabase migration/RLS tests, Python worker scaffold, versioned contracts, static synthetic research story, CI, no LLM. **Pass:** clean setup, CI and mobile story comprehension prototype.

**PR2: Data feasibility proof.** Verify 2–3 chosen UCITS share-class identities and history, documented FX and company/official fund pages, one official historical policy release with amendment, rights matrix. **Pass:** sample real source/quote records are accurately ingested and linked; unknown data blocks.

**PR3: Accounting and evidence validation.** Synthetic portfolio ledger and cashflow-matched benchmark; claim verification validator; negative tests for invalid citation, duplicated import, missing FX. **Pass:** replay correctness and rejected unsupported claim; published pages cannot bypass review.

## Research milestones and trade-offs
- 'Automated article pipeline' is not a milestone until verified claims and human editorial gating exist.
- 'Multi-agent network' is not a milestone. A bounded retrieval, analytical and adversarial role exists only if it improves evaluation relative to a simpler baseline.
- 'Self-learning' is not a one-time model feedback prompt. Must demonstrably preserve original forecasts and independently test changed rules.
- 'Mock accounts' need only a ledger engine, not broker paper logins, individual AI instances or simulated fake market feeds.
- Content and learning can launch while investment alpha is unproven. Never label the service an outperformer because of a profitable initial cohort.

## Release KPIs: not vanity metrics
**Human value:** comprehension (conclusion + uncertainty), educational lesson clarity, voluntary helpful return visits, reported confidence in ability to understand (not market certainty). **Truth:** source support coverage, citation mismatch detection, correction time, unanswered challenges, data freshness. **Research:** preregistered trial status, outcomes and calibration vs baselines. **Money:** ledger reconciliation, total-return accuracy, FX coverage. **Reliability:** job success, restore drills, spend and security incidents.

## Scope guardrails
At most 1–3 verified causal domains during first complete slice; the extensive ontology is future coverage. At most 2–3 active quantitative methodologies until verified end to end. At most several controlled virtual experiment cohorts until evaluation is proven. Only build capabilities that directly support the end-to-end research trust chain, core wealth use or comprehension tests.

## Launch blocking criteria
Cannot launch publicly if: unsupported material investment facts render; unverifiable fund identity is treated eligible; any cross-tenant data leak is possible under tests; source-rights unverified for distribution; correction audit absent; method changes silently modify champion results; portfolio wrong when FX missing; privacy/terms/regulatory classification lacks review; founding entitlement contract not published before promotion.

## Founder discipline
Maintain `DECISIONS.md` (ADRs), `SOURCE_RIGHTS.csv`, `METHOD_REGISTER.csv`, `KNOWN_UNKNOWNS.md`, `INCIDENTS.md`, `MODEL_CHANGELOG.md`, and `RESEARCH_SCORECARD.md`. Update charter only on genuine strategic decision, not each passing idea. Small discoveries modify the appropriate subsystem spec, never erase earlier commitments.
