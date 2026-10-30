# Macro Intelligence methodology programme

**Status:** canonical for macro methodology (ADR 027)  
**Owner:** founder  
**Last verified:** 25 October 2026  
**Must not contradict:** `docs/00_READ_ME_FIRST.md`, ADR 005, ADR 006, ADR 011, `docs/03_RESEARCH_ENGINE_AND_METHODS.md` except where ADR 027 supersedes the 18 October 2026 macro-method pause.

Progress stays in `docs/07_BUILD_BACKLOG.csv`. Methodology status stays in `docs/macro/QUANTITATIVE_METHOD_REGISTER.csv`. Investment-factor rows stay in `docs/08_METHOD_REGISTER.csv`. Those are different registers.

## What Macro Intelligence must accomplish

Macro Intelligence estimates the state and risks of economies from published quantitative methods. It answers questions those methods were built to answer: where activity is, whether a series has turned, what a current-quarter estimate is, and how large a stated probability is. It does not produce a proprietary combined score, and it does not optimise historical equity returns.

ETF Intelligence and My Wealth remain. A macro result is not an allocation, a fund selection, or a broker instruction.

## Methodology determines the data

A series is acquired because a named method requires it. Geography waves are not the priority. An available series is not a substitute for a required series unless the substitution is written down, with the economic and statistical difference stated.

## Economic conclusions come from algorithms

A language model may help locate papers, write code, debug, and draft documentation. It must not be given observations and asked whether an economy is strengthening, deteriorating, or entering a recession. That decision is closed by ADR 027 and is not reopened here.

Published prose in the product must restate a stored calculation, including its uncertainty and the limits of the method. `publication_allowed` stays false until the existing editorial gate is met. This programme does not open publication.

## Two different firsts

| Role | Method | What it is |
|------|--------|------------|
| Engineering pilot, built first | Monthly Bry–Boschan (1971) on `fed.g17.IP.B50001.S` | Proof that one published algorithm can be specified, checked, stored, replayed, rerun, and monitored |
| First strategic intelligence milestone | A specified Stock–Watson dynamic factor model | The first method intended to measure co-movement in activity, after its data contract is verified |

The pilot does not measure current activity, nowcast GDP, or classify the US business cycle for investment use. Harding–Pagan quarterly BBQ is a later quarterly method. It is not run on monthly industrial production. Static principal components and the Chicago Fed National Activity Index sit inside the factor family. They are not a substitute for the dynamic-factor milestone. Kalman filtering is an estimator, not a separate product.

The NBER US business-cycle chronology is an external diagnostic. Overlap with it is reported. It is not proof that the code is correct, and it is not an exact-match acceptance test.

## Families and what each can add

Activity and dating methods describe co-movement or turning points. They do not, by themselves, forecast asset returns. Nowcasts estimate a current or recent national-accounts outcome. Recession-probability models estimate a stated event probability. Financial-conditions and credit-gap methods summarise financial or leverage pressure. Inflation-trend methods separate a slow component from monthly noise. Structural-break tests ask whether a relationship has shifted. Portfolio methods in `docs/08_METHOD_REGISTER.csv` are outside this implementation sequence.

## Engineering lifecycle

These states are not the evidence ladder in `docs/03_RESEARCH_ENGINE_AND_METHODS.md`. A model can be implemented without being validated, and historically checked on revised data without being fit for operational use.

1. Candidate identified.
2. Original research verified.
3. Mathematical specification documented.
4. Data requirements established.
5. Required data available and quality-checked.
6. Model implementation complete.
7. Numerical verification passed.
8. Historical validation completed.
9. Results persistently stored.
10. Automated recalculation operational.
11. Monitoring operational.
12. Validated and operational.
13. Suspended, superseded, or retired.

### Crosswalk to the evidence ladder

| Engineering state | Evidence-ladder label it may support |
|-------------------|--------------------------------------|
| 2–3 | `documented` |
| 6–7 | `implemented` |
| 7, when a published number or fixture is reproduced | `replicated` |
| 8, and only with a point-in-time design when a real-time claim is made | `historically_evaluated` |
| 10–12, frozen forward | `prospectively_testing`, then `prospectively_supported` only against a predeclared hurdle |
| 13 | `degraded` or `retired` |

Revised-data numerical correctness does not justify `historically_evaluated` as a real-time forecast claim.

## Data-dependency contract

Each method dossier names the series, the provider, the economic definition, the frequency, the units, the sample length, the alignment, the transformation, the revision rule, the release timing where it matters, the rights row, and whether a live and a historical evaluation are possible. Proxies are forbidden unless that contract records them.

Shared sources are reused. A second pipeline for the same official series is not created.

## Model identity

A published name, an Aqil implementation, and a fitted run are different objects.

Minimum metadata, already largely present on `research.research_runs`:

- Methodology identifier and published reference.
- Implementation version and implementation hash.
- Configuration and parameter hash.
- Estimation or calibration window, when the method estimates parameters.
- Input dataset version, transformation, and the observation identifiers used.
- Vintage policy: `latest_revised` or `point_in_time`.
- Output schema identifier.
- Validation status.

The pilot stores this on the existing run row. It does not add a model-registry schema.

The Methodologies page reads `apps/web/src/lib/research/methodology-catalogue.ts`. That file is a presentation map, not a second register. A register row appears as a card, or in `EXCLUDED_REGISTER_ROWS` with a reason. Supporting techniques for the dynamic factor, and the deferred portfolio row, are excluded. Planned cards have no research-run query and must not show a calculation. Moving a card from planned to in development means the research system has a versioned output, the catalogue names that output kind and the run identifiers, and a signed-in session may see that stored calculation. `publication_allowed` stays false until the editorial gate is met. A signed-out session does not receive the calculation. A matching method identifier alone does not promote the card.

## Persisted results

`research.research_runs`, `research.research_run_observations`, and `workers/research/src/aqil_research/persistence/reproduce.py` are the envelope for the pilot. The JSON payload holds method-specific outputs. A turning-point list, a factor value, a nowcast, and a break date do not share one numeric column.

Each run records the evaluation date, the calculation time, the information cutoff the method actually used, the input observation links, the provenance class, the execution status, and numerical diagnostics the method defines. `publication_allowed` remains false.

There is no `jobs` table and no `forecast_contracts` table in `supabase/migrations/`. `docs/04_ARCHITECTURE_AND_DATA.md` describes a job queue. That queue is not a current capability.

## Recalculation

Recalculation frequency follows the economics of the series, not a clock.

- New or revised observations of an input series.
- A scheduled run at the series frequency, when a release can arrive without a detected row change.
- A controlled manual research run.

The pilot reruns the monthly Bry–Boschan procedure when G.17 is newly stored or revised, or on a documented monthly run of that one method. That is one entry point. It is not a generic scheduler and not the architecture document's job queue.

Distinguish a new inference with fixed parameters from re-estimation. Bry–Boschan has no estimated parameters. A dynamic factor model does. Re-estimation is a separate, versioned event.

## Monitoring

A successful process exit is not health.

The pilot monitors: input completeness for `fed.g17.IP.B50001.S`, a failed or incomplete run, a breach of the documented censoring rules, a replay mismatch, and a stale input relative to the latest stored G.17 month. Later methods add their own checks. A factor model watches convergence and sign or scale conventions. A probability model watches outputs outside the unit interval. A forecast watches the error when the outcome is published. None of those checks are built in this documentation pass.

## Acceptance tests

Every method has its own tests. There is no universal accuracy threshold.

Required patterns:

- Reproduction of the published procedure or a controlled fixture.
- An independent reference where one exists.
- Historical evaluation designed for what the method claims.
- Point-in-time validity before any real-time claim.
- Out-of-sample checks before a forecasting claim.
- A simpler benchmark where the method claims skill.
- Written failure conditions.

## Point-in-time meanings

**Retrospective analysis.** What the method says about history using data available today. Operational Aqil rows are `latest_revised`. A latest-revised row is not a vintage.

**Real-time reconstruction.** What the method could have said on a past date using only information available then. That requires vintages of the observations, of the transformations, of the estimation window, and of any classification used as a label.

**Genuine historical forecasting.** A forecast recorded at a cutoff, scored against the outcome that later occurred.

On 25 October 2026 a read-only query of local `postgres` found 35,735 observation rows: 35,648 from live retrievals and 87 from fixture retrievals. 35,720 rows are `latest_revised` and 15 are `provider_vintage`. The 15 vintage rows are the known unemployment fixtures, not an operational panel. FRED/ALFRED remains technically blocked in `docs/sources/SOURCE_RIGHTS.csv`. The as-of selector in `workers/research/src/aqil_research/vintages/asof.py` is implemented and tested on synthetic rows. Live macro methods refuse point-in-time mode when their inputs are latest-revised files.

Phased validation:

1. Mathematical correctness on revised history and fixtures.
2. Real-time reconstruction only after a lawful vintage source is stored.
3. Forecast skill only from forecasts that were frozen before the outcome.

Training windows, standardisation moments, parameter estimates, feature choices, hyperparameter choices, and label chronologies are all inside the information set. Using today's NBER dates as if they were known in real time is look-ahead. Using them as an external benchmark of a retrospective dating is allowed, and must be labelled as that.

ALFRED and the Philadelphia Fed real-time data sets are candidate later sources. They are not held, and ALFRED is not an approved ingest path.

## What already exists

The observation path is implemented: rights, adapters, `research.try_insert_observation`, manual `npm run research:refresh`, and append-only observations. Twenty-three series are operational in `docs/sources/MACRO_COVERAGE.csv`. The same read-only query found 34,859 live rows on those 23 dataset identifiers, equal to 34,859 distinct periods. OECD G20 CLI has 789 stored rows and is not operational. `research.research_runs` has 25 rows. The hosted project was not queried in this pass. The 24 October handover still describes the host as five migrations and empty research tables. Treat that as the last host read, not as a new host inspection.

Nine deterministic methods are registered in `workers/research/src/aqil_research/methods/registry.py`. Sahm (2019) is the only recognised published rule among them. The labour, prices, production, and credit readings are ranks and twelve-month changes. They are not a dynamic factor model. The worker dependencies are `httpx`, `psycopg`, and `pydantic`. NumPy, pandas, and a Kalman library are not installed. There is no production cron.

US industrial production `fed.g17.IP.B50001.S` is 1,293 `latest_revised` months, January 1919 to September 2026, one row per month. US unemployment in the live file is 44 months from January 2023. US GDP is not stored. Euro-area real GDP is stored quarterly.

## Shared work the pilot may add

Only what the pilot itself needs, and what the factor-model milestone will reuse without a platform:

- A written vintage policy on the run (`latest_revised` for the pilot).
- Replay of a stored run from linked observation identifiers.
- A method-specific monitor for this run.
- One recurring entry point for this series.

A reference chronology used as a diagnostic may be stored as research input with its publication date. It is not a second modelling framework.

## Related

- `docs/macro/QUANTITATIVE_METHOD_REGISTER.csv`
- `docs/macro/DATA_DEPENDENCIES.md`
- `docs/macro/FIRST_CAMPAIGN_BRY_BOSCHAN_IP.md`
- `docs/macro/dossiers/`
- `docs/11_ARCHITECTURE_DECISIONS.md` ADR 027
