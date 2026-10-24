# First campaign: monthly Bry–Boschan on industrial production

**Status:** 25 October 2026. The 1971 volume still does not print the Spencer weights or the twelve-month alignment, so `BRY_BOSCHAN_MONTHLY_1971` refuses to date. A labelled variant, `BRY_BOSCHAN_SPENCER15_VARIANT`, uses the Macaulay 1931 weights and the Otsu 2020 twelve-month placement. It is not the 1971 listing and not a FORTRAN replica.  
**Owner:** founder  
**Last verified:** 25 October 2026  
**Series:** `fed.g17.IP.B50001.S`

The pilot is an engineering validation. The first strategic intelligence milestone is the Stock–Watson dynamic factor model in `docs/macro/dossiers/STOCK_WATSON_DFM.md`, after `AQ-101`.

## 1. Specification

Monthly procedure in Bry and Boschan, NBER, 1971, chapter 2. The frozen card is in `docs/macro/dossiers/BRY_BOSCHAN_MONTHLY.md`. Endpoint, phase, and cycle rules that the chapter prints are copied there. The full volume, chapters c2145 to c2150, does not print the Spencer coefficients or the twelve-month alignment, so `BRY_BOSCHAN_MONTHLY_1971` still refuses. The labelled variant is specified in the dossier and is not a substitute claim that the book printed the constants.

## 2. Why this is first

G.17 is already stored: 1,293 `latest_revised` months, 1919-01-01 to 2026-09-01, one row per month, read-only query on 25 October 2026. The frequency matches the monthly procedure. The algorithm has no estimated parameters, so the lifecycle can be proved without a statistical library or a vintage panel.

## 3. Research still required before code

Do not code another Spencer curve, and do not describe `BRY_BOSCHAN_SPENCER15_VARIANT` as the 1971 listing. The weights are Macaulay's printed coefficients, not a later software package.

## 4. Reuse

- Rights and the G.17 adapter. No new ingest.
- `research.economic_observations` and live retrievals only. Exclude fixture retrievals.
- `execute_research_run` / `research.research_runs` / observation links / `reproduce.py`.
- `publication_allowed` false. The claim verifier stays fail-closed.
- Do not edit the four reading methods or Sahm as part of this pilot.

## 5. Series

Only `fed.g17.IP.B50001.S`. Seasonally adjusted total industrial production index, as stored. Do not re-seasonally adjust. Do not convert to quarters.

## 6. Data already suitable

The revised monthly index above. Retrospective use only.

## 7. Missing data

None for the retrospective pilot. Vintages are missing and are not required for mathematical correctness. They are required before any claim about what the procedure would have dated in real time.

## 8. Preprocessing

Sort by `period_start`. Require one live `latest_revised` value per month in the interior of the sample. Fail on a gap. Do not interpolate. Record the first and last month used.

## 9. Implementation approach

One method module, one version, one hash, following `methods/protocol.py`. Pure Python unless AQ-094 shows the Spencer or MCD step cannot be reproduced that way. No generic dating framework. No quarterly BBQ mode.

## 10. Reference to reproduce

A fixture constructed from the frozen rules, and a chapter output table if AQ-094 transcribes one. An external Bry–Boschan program is a reference only after it is shown to match the chapter. The NBER reference chronology is not this reference.

## 11. Numerical verification

Same fixture, same dates, on two implementations or on a transcribed chapter table. Tolerance is exact dates, not a correlation. A failed date fails the build.

## 12. Historical evaluation

Run on the stored G.17 sample. Publish the peak and trough list as a research-run payload. This is retrospective on revised data.

## 13. Point-in-time

`analysis_mode` is `latest_revised`. The run states that later revisions of G.17 can move the dates and that the latest six months may be undated under the chapter's endpoint rule. Do not select point-in-time mode. The selector would drop these rows.

## 14. Persistence

One immutable run per evaluation. Payload: implementation version, month range, peak dates, trough dates, phase lengths, rules that removed candidate turns, and input observation identifiers. Parameter vector: none.

## 15. Recurring execution

After a G.17 refresh that inserts or would have revised a month, run this method once. If the input hash is unchanged, record unchanged rather than a duplicate payload. Also allow one documented monthly invocation if a release might have been missed. Do not add `jobs`, a queue, or a cron for other methods.

The current refresh is manual (`npm run research:refresh`). The pilot adds a hook for this method on that path, or a single command the operator runs after refresh. It does not claim unattended production scheduling. Hosted refresh remains subject to the U0 approval in `docs/runbooks/U0_HOSTED_RELEASE.md`.

## 16. Monitoring

Fail the health of this method when:

- the latest stored G.17 month is absent from the run's input and the run is not an explicit unchanged replay of that month
- the run errors
- a stored peak and trough violate the frozen alternation, fifteen-month cycle, or five-month phase rule
- replay from the linked observations differs
- fixture retrievals were included

A green process exit is not enough. NBER disagreement is not a health failure.

## 17. Gates

| Gate | Pass |
|------|------|
| Specification | AQ-094 card matches chapter 2, and quarterly BBQ is stated as out of scope |
| Numerical | Fixture dates match |
| Persistence | Run row, observation links, replay match |
| Recurring | Second invocation is idempotent |
| Monitoring | The failure cases above are tested |
| NBER | A diagnostic table exists and the acceptance text says overlap is not a pass-fail rule |
| Claim limit | Copy states specific cycles in industrial production, revised data, not a reference-cycle call and not a real-time call |

## 18. Risks

The dossier summary can drift from the program listing. Spencer weights are easy to replace with a centred moving average and still "look cyclical". Endpoint censoring will leave the current months undated and must not be filled by judgement. G.17 revisions can change history. The local database password and host were not part of this brief. Hosted observations were not confirmed in this pass.

## 19. Smallest end-to-end deliverable

AQ-094 card, fixture test, one local run on live G.17, replay, idempotent second run, and a monitor test. No user-interface change is required for that deliverable. No publication.

## 20. Before the Stock–Watson milestone

AQ-099 monitoring is operational. AQ-101 has named the paper, the equations confirmed against the PDF, and each series as held, missing, or an explicit non-substitute. Unemployment backfill and a three-month yield are not pilot work. Harding–Pagan has no task on this path.

Shared pieces worth keeping because the factor model will use them: run versioning, observation links, replay, a written `latest_revised` vintage policy, and a method-specific monitor shape. Not worth building now: a job queue, a Kalman service, a generic model registry, or a vintage warehouse.
