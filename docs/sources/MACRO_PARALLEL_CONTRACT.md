# Parallel macro dataset sprint contract

Status: sprint instruction. Owner: integration owner. Last verified: 22 October 2026.

This file tells the six workstreams what they may change during this sprint. It is not a research framework, not a schema, and not a documentation authority. Product truth stays in the code and the canonical docs. If this note and the code disagree, the code wins:

- `EconomicObservation` schema 1.0 in `workers/research/src/aqil_research/contracts/observation.py`
- `REGISTER_COLUMNS` and `FIRST_LIVE_OPERATIONS` in `workers/research/src/aqil_research/sources/rights.py`
- `collect_registered_adapter` in `workers/research/src/aqil_research/collection/service.py`
- `assert_series_fetch_usable_for_ingest` in `workers/research/src/aqil_research/collection/series_fetch_gate.py`
- `research.try_insert_observation` in `supabase/migrations/20261017110000_create_research_schema.sql`

Do not push, deploy, schedule a refresh, or apply a hosted migration. Do not commit `.cursor/rules/mcp.json`.

## Frozen observation contract

`EconomicObservation` schema 1.0 is frozen. `schema_version` stays `1.0`. No migrations. No new columns. No edits under `workers/research/src/aqil_research/contracts/` or `supabase/migrations/`.

A current provider file that has no historical vintages is stored as `series_provenance=latest_revised` with `availability_precision=unknown`. Those rows must not set `earliest_model_available_at`. Do not invent `provider_vintage` rows. A preliminary printed value stays `quality_status=observed` on that latest-revised row. Record the revision limitation in the rights fragment.

`raw_value` is a finite decimal string. Units, period, geography, frequency, and seasonal adjustment are required fields on every stored row.

## Rights fragments

Workstreams write rights fragments. They do not edit `docs/sources/SOURCE_RIGHTS.csv`. The integration owner merges fragments later.

Each fragment is `docs/sources/fragments/<source_id>.csv`: the header is exactly `REGISTER_COLUMNS`, in that order, and the file contains one data row for that `source_id`. `evidence_urls` are HTTPS URLs separated by `|`. `terms_url` is HTTPS and appears inside `evidence_urls`. `access_url` is HTTPS.

`m1_role=first_live_provider` requires every operation in `FIRST_LIVE_OPERATIONS` to be `permitted`:

- `automated_access`
- `internal_computation`
- `raw_data_retention`
- `historical_archiving`
- `redistribution`
- `commercial_publication`

`attribution` is `required`. `operational_status` is `enabled`, because ingest refuses a disabled source. `ai_processing` and `ai_model_training` are outside that clearance. Leave them `unknown` unless the cited terms explicitly permit them. Unknown and prohibited decisions block the operation they name.

## Persistence

Persist only through `collect_registered_adapter`, which inserts with `research.try_insert_observation`. A partial payload fails ingest (`allow_partial_payload` is false). Official gaps are omitted periods. They are never stored as zero and never interpolated. Board `ND` is an omitted period.

## Value identity

Unchanged values keep the first stored identity. A changed value is a new row. Copy that behaviour inside the adapter package: when the stored finite decimal for the same period matches the incoming value, reuse that row’s observation id, provider vintage date, and release identity; when the value differs, or no row exists for the period, allocate a new observation id.

Do not edit `workers/research/src/aqil_research/adapters/fed_sloos/stability.py`. Do not add a shared stability module, and do not generalise that file into a framework.

A second fixture run through `collect_registered_adapter` inserts nothing when the payload is unchanged.

## File ownership

Each workstream may add only:

- its adapter package or packages under `workers/research/src/aqil_research/adapters/`
- its tests under `workers/research/tests/`
- one small committed fixture
- its rights fragment or fragments under `docs/sources/fragments/`

Forbidden for every workstream:

- `workers/research/src/aqil_research/contracts/`
- `workers/research/src/aqil_research/persistence/`
- `workers/research/src/aqil_research/methods/`
- `workers/research/src/aqil_research/workflow/refresh.py`
- `docs/sources/SOURCE_RIGHTS.csv`
- `supabase/migrations/`
- `apps/web/`
- Census adapters (`workers/research/src/aqil_research/adapters/census_adv_orders/`)
- `workers/research/src/aqil_research/adapters/fed_sloos/`
- the BLS API client and the unemployment series (`workers/research/src/aqil_research/adapters/bls/`, series `LNS14000000`, dataset `bls.ln.LNS14000000`)
- the existing CPI Atom feed (`workers/research/src/aqil_research/adapters/bls_cpi/`, source `bls_cpi_archive`)
- any adapter package assigned to another workstream
- provider archives and zip files

The integration owner, on local `main` in `C:\Users\gamer\aqil` only, later merges fragments into `SOURCE_RIGHTS.csv`, registers successful collectors in `workflow/refresh.py`, and runs live ingest. One failed source must not cancel the others.

## Workstreams

1. **BLS CPI.** Package: `adapters/bls_cpi_series`. Candidate `CUSR0000SA0`, bound only after `cu.series` confirms it. Flat file under `https://download.bls.gov/pub/time.series/cu/`. Send user agent `AqilResearch/1.0`. This dataset is not the CPI Atom feed.

2. **BLS labour.** Packages: `adapters/bls_payrolls` and `adapters/bls_jolts`. Payrolls candidate `CES0000000001`, bound only after `ce.series` confirms it (total nonfarm, seasonally adjusted, thousands). Job openings `JTS000000000000000JOL`, taken from `jt.data.2.JobOpenings` and filtered to that one series (seasonally adjusted, total nonfarm, level in thousands). A preliminary footnote stays an observed `latest_revised` value. It is not an earlier vintage.

3. **Fed G.17.** Package: `adapters/fed_g17`. Total industrial production, seasonally adjusted, index. Read the description from the Board package. Never use FRED. Never use the name `INDPRO`. Do not commit the archive. If the Board URL is not HTTP 200, stop. Do not switch provider.

4. **Fed H.15.** Package: `adapters/fed_h15`. Two `source_id` values, so two fragment files. Bind `H15/H15/RIFSPFF_N.M` (federal funds effective rate, percent per year, monthly) and `H15/H15/RIFLGFCY10_N.M` (10-year Treasury constant maturity, percent per year, monthly) only if the downloaded file repeats those descriptions. `ND` is omitted. No spread. No Treasury XML. No Fiscal Data average rates. Daily business-day yields stay out of this sprint.

5. **Fed H.8.** Package: `adapters/fed_h8`. One seasonally adjusted bank-credit series whose description is confirmed in the Board package. Never use FRED. SLOOS remains the lending-standards series and is not edited.

6. **ECB SDW.** Package: `adapters/ecb_sdw`. One monthly euro-area series, bound only after metadata shows the ECB or the ESCB compiles it. Prefer ECB-compiled seasonally adjusted HICP when the metadata says the ECB compiles it. Do not store Eurostat-origin HICP on the ECB rights row alone.

## Not assigned

Census, BEA, FRED, ALFRED, Sahm changes, the Bank of Japan, ETF holdings, UI, and new methods. October 2025 remains an absent unemployment month. Nothing is interpolated.

## Database

Agents must not write the development database (port 55432, database name `postgres`). Tests must not open that database. Live ingest of merged sources is the integration owner only. Live row counts are recorded only by the integration owner.

## Method compatibility

Current methods stay unchanged. Compatibility notes for every new series say that none of them consume the new dataset ids:

- Sahm requires `bls.ln.LNS14000000`
- SLOOS requires `fed.sloos.SUBLPDCILS_N.Q`
- Census advance orders requires `census.m3.adv.MDM.NO`
- macro-conditions requires those three dataset ids
- period-level change requires `bls.ln.LNS14000000`

Do not edit those methods so that they accept the new series.

## Done for a workstream

A downloaded file is not done. The workstream shows a rights fragment that loads, observations normalised to schema 1.0, retrieval metadata, omitted periods listed, a second fixture ingest that inserts nothing, tests that do not open the database named `postgres`, and the compatibility note above.
