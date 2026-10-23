# Macro read contract for ETF instruments

Status: proposed read boundary. Owner: ETF orchestrator. Last updated: 23 October 2026.

This note says what a later macro change may read from schema `instruments`. It does not apply that change. `EconomicObservation` is unchanged. `forward.etf_*` is unchanged. Macro code, `docs/sources/SOURCE_RIGHTS.csv`, and the preserved database `postgres` are unchanged.

## What macro may later query

A future macro reader may select only these facts for a share class, and only from `instruments`:

- benchmark id, from `instruments.dated_characteristics` where `characteristic_code` is `benchmark_id` and `availability` is `cited`. The value is the `instruments.benchmarks` id. A null or missing row is not a guess
- exposure class, from `instruments.exposure_snapshots.exposure_class`
- inception date, from `instruments.share_classes.inception_date`
- evidence status, from `instruments.share_classes.evidence_status` and from `instruments.assessments.evidence_status`

Those reads are not authorised until this contract is accepted on the macro branch. Phase A does not add a macro query.

Missing inception, missing benchmark id, or evidence status other than `cited` stays missing. Macro must not fill the gap from a ticker, a fund name, or a benchmark return.

## What macro must not do

- Macro must not insert, update, or delete any table in schema `instruments`.
- Macro must not read `instruments.holdings_snapshots` or `instruments.holdings_lines` unless the snapshot's `rights_gate` is `permitted` and the source fragment has `automated_access=permitted` and `redistribution=permitted`. `prohibited` and `unknown` fail that gate. `workers/research/src/aqil_research/etf/contracts/rights.py` is the helper. A holdings row that failed the gate is not a partial input.
- Macro must not read `instruments.fund_returns` as if they were benchmark returns, or `instruments.benchmark_returns` as if they were the fund's own return.
- Macro must not treat trading currency, base currency, hedge status, or distribution policy as the same field.
- Macro must not write My Wealth, Today, or Evidence from this schema in this phase.

## Series that stay separate

Fund NAV or total return belongs to one share class and cannot start before that share class's inception date. Benchmark history belongs to `instruments.benchmarks` and may use a different currency, return type, and reinvestment convention. A price index and a total-return index are different `return_convention` values. Neither is an `EconomicObservation`.
