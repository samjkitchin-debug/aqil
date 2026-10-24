# Macro analytical contract

Status: sprint instruction. Owner: integration owner. Last verified: 23 October 2026.

This file tells the four reading workstreams what they may calculate and which files they may add. It is not a research framework, not a schema, and not a documentation authority. Product truth stays in the code. If this note and the code disagree, the code wins:

- `MethodExecutionResult`, `MethodContext`, and `AnalyticalMethod` in `workers/research/src/aqil_research/methods/protocol.py`
- `AnalysisMode` and `EconomicObservation` schema 1.0 in `workers/research/src/aqil_research/contracts/observation.py`
- `select_as_of_series` in `workers/research/src/aqil_research/vintages/asof.py`
- `default_method_registry` in `workers/research/src/aqil_research/methods/registry.py`
- `publication_allowed` on `ResearchRun` in `workers/research/src/aqil_research/pipeline/models.py`

Do not push, deploy, schedule a refresh, or apply a hosted migration. Do not reset the preserved database on port 55432.

## Verified live baseline

Queried read-only on 23 October 2026 at `postgresql://research_worker:research_worker@127.0.0.1:55432/postgres`, joined to `research.source_retrievals` with `collection_mode = 'live'`. Row counts equal distinct `period_start` counts. Every listed row has `series_provenance = latest_revised`. These counts, units, and provenance values match the stored rows. October 2025 (`2025-10-01`) is absent for unemployment and CPI-U. September 2025 and September 2026 are present for both. Job openings have no live row after August 2026. HICP has no live row after December 2025. Both H.15 series have `seasonal_adjustment = unknown`. No live Census observations are stored.

| Dataset | Count | Minimum `period_start` | Maximum `period_start` | Unit | `seasonal_adjustment` |
| --- | ---: | --- | --- | --- | --- |
| `bls.ln.LNS14000000` | 44 | 2023-01-01 | 2026-09-01 | `percent` | `seasonally_adjusted` |
| `bls.cu.CUSR0000SA0` | 956 | 1947-01-01 | 2026-09-01 | `1982-84=100` | `seasonally_adjusted` |
| `bls.ce.CES0000000001` | 1053 | 1939-01-01 | 2026-09-01 | `thousands` | `seasonally_adjusted` |
| `bls.jt.JTS000000000000000JOL` | 309 | 2000-12-01 | 2026-08-01 | `thousands` | `seasonally_adjusted` |
| `fed.g17.IP.B50001.S` | 1293 | 1919-01-01 | 2026-09-01 | `index_2017_100` | `seasonally_adjusted` |
| `fed.h8.B1001NCBA` | 2806 | 1973-01-03 | 2026-10-07 | `usd_millions` | `seasonally_adjusted` |
| `fed.h15.RIFSPFF_N.M` | 867 | 1954-07-01 | 2026-09-01 | `percent_per_year` | `unknown` |
| `fed.h15.RIFLGFCY10_N.M` | 882 | 1953-04-01 | 2026-09-01 | `percent_per_year` | `unknown` |
| `ecb.icp.M.U2.Y.000000.3.INX` | 348 | 1997-01-01 | 2025-12-01 | `index, 2015 = 100` | `seasonally_adjusted` |
| `fed.sloos.SUBLPDCILS_N.Q` | 146 | 1990-04-01 | 2026-07-01 | `percent_net_tightening` | `not_seasonally_adjusted` |

None of these files is a vintage panel.

## Result contract

Results use `MethodExecutionResult`. No new schema. Do not add fields to that dataclass, to `EconomicObservation`, or to `ResearchRun`.

A sufficient `calculation` names the transformation and the stored unit. `observation_ids` lists every observation used. An insufficient result sets `calculation` to `None`, `observation_ids` to empty, and `missing_reason` to the failed window.

`MethodContext.analysis_mode` is `latest_revised`. A point-in-time request is insufficient because these files are not vintage panels. `select_as_of_series` skips `series_provenance = latest_revised`, so a `point_in_time` request has no eligible rows from this baseline.

`causal_hypothesis` says that no causal mechanism is established. `investment_implication` is `no_action` when the window is sufficient and `insufficient_evidence` when it is not. These four readings stay separate. There is no composite score.

`publication_allowed` stays false on the research run. Evidence copy says the reading is internal: “The reading is internal.” Today is unchanged. Workstreams do not render Evidence.

A missing endpoint fails that window. Do not interpolate. Do not invent the missing observation, and do not fill it with zero.

## Method ids and dataset ids

These four method ids are new. They are not registered in this step. Version each one `1.0.0`.

### `LABOUR_MARKET_CONDITIONS` 1.0.0

Inputs:

- `bls.ln.LNS14000000` (`percent`, seasonally adjusted)
- `bls.ce.CES0000000001` (`thousands`, seasonally adjusted)
- `bls.jt.JTS000000000000000JOL` (`thousands`, seasonally adjusted)

Report each series on its own latest stored month. A joint reading uses only months present in all three. A window that needs October 2025 unemployment is insufficient. The 12-month change and the rank in the stored latest-revised history are computed only when both endpoints exist.

### `PRICES_AND_POLICY` 1.0.0

Inputs:

- `bls.cu.CUSR0000SA0` (`1982-84=100`, seasonally adjusted)
- `fed.h15.RIFSPFF_N.M` (`percent_per_year`, seasonal adjustment unknown)
- `fed.h15.RIFLGFCY10_N.M` (`percent_per_year`, seasonal adjustment unknown)

CPI-U 12-month percent change is computed only when both index months exist, including September 2025 to September 2026. Federal funds and the 10-year yield are levels in percent per year and one-month changes in percentage points. Do not subtract them. Do not call anything a near-term forward spread. Do not compute a real rate.

HICP `ecb.icp.M.U2.Y.000000.3.INX` is not an input. Name it only as a separate series ending December 2025 (`index, 2015 = 100`).

### `INDUSTRIAL_PRODUCTION_ACTIVITY` 1.0.0

Input: `fed.g17.IP.B50001.S` (`index_2017_100`, seasonally adjusted).

Report the level, the 12-month percent change, and the rank in the stored latest-revised history. A missing endpoint fails that 12-month window. This is production, not GDP. Census is absent.

### `CREDIT_STANDARDS_AND_VOLUMES` 1.0.0

Inputs:

- `fed.sloos.SUBLPDCILS_N.Q` (`percent_net_tightening`, not seasonally adjusted)
- `fed.h8.B1001NCBA` (`usd_millions`, seasonally adjusted)

Report the latest SLOOS share and the prior quarter, beside the latest H.8 week and a 52-week change in millions of dollars when that week exists. A missing endpoint fails that comparison. Do not convert a survey balance into dollars.

## Unchanged methods

Do not edit Sahm (`SAHM_UNEMPLOYMENT_GAP`), `PERIOD_LEVEL_CHANGE`, `SLOOS_CIL_LENDING_STANDARDS`, Census (`CENSUS_ADV_DURABLE_ORDERS`), or `MACRO_CONDITIONS_PANEL` 1.0.0.

**25 October 2026.** The sentence that `default_method_registry` registers only those five is out of date. The registry also registers the four reading methods and `MACRO_READING_SYNTHESIS` is produced by `workflow/record_macro_readings.py`. Code is the registry. This contract's ownership rules for the October reading sprint are historical. New macro-method priority is ADR 027 and `docs/macro/00_METHODOLOGY_PROGRAMME.md`, not a further edit of these readings.

## File ownership

Each agent may add only:

- its method module under `workers/research/src/aqil_research/methods/`
- its tests under `workers/research/tests/`
- one small fixture
- `docs/sources/fragments/<method_id>.json`

Tests use fixtures. They do not open the database named `postgres`.

Forbidden for every workstream:

- `workers/research/src/aqil_research/methods/registry.py`
- `workers/research/src/aqil_research/methods/protocol.py`
- `apps/web/`
- `supabase/migrations/`
- `docs/sources/SOURCE_RIGHTS.csv`
- `workers/research/src/aqil_research/workflow/refresh.py`
- the preserved database on port 55432
- the five existing method modules

The integration owner later merges, registers the four methods, runs them once on the stored observations, and renders Evidence. `publication_allowed` stays false. Today stays unchanged.
