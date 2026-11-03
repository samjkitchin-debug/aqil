# ETF protocol

Protocol `ETF-PROT-001` version 1 and event definition `EVT-DEF-002` version 1.
Specification commit `401f7e48eb08a89a7e63a8338f61fa94276d6dce`.
Protocol hash `993e58f82828f4c8d4cb1e1b27c29e960080f52f0d9f5c1d43d802b791e65de4`.
`EVT-DEF-001` hash `3844aff160a7f6fac7fb4c966707a313b6e8c89f4bb04cee6a72cb4d97275114` is unchanged.
`EVT-DEF-002` hash `f1f10b25f1d741102e648bf0fb4cf6e4868629958edae6a6cda988327cc57c32`.

The specification commit precedes the stored scores. Reproduction is `uv run python -m aqil_research.long_horizon.etf_protocol`. The second run printed `unchanged` and inserted 0 events and 0 trials.

## Catalogue

`EVT-DEF-002` was catalogued for every listing that has stored adjusted closes. That is 19 listings. `INRG` has no listing and no prices. `EUNA` was catalogued and was not scored as a US-dollar relative result, because foreign-exchange rows are still 0.

| Family | Events |
|---|---:|
| sustained_decline | 478 |
| persistent_bear | 25 |
| failed_recovery | 19 |
| trend_reversal | 388 |
| volatility_transition | 1000 |
| Total | 1910 |

Sustained-decline horizons: 392 at 1 month, 72 at 3 months, 13 at 6 months, 1 at 12 months, and 0 at 24 and 36 months. The 24-month and 36-month rows are stored with event count 0. Family-count rows: 190. No new event has `publication_allowed` true. `EVT-DEF-001` still has 1,749 events.

## Trials

The declared grid and the stored trial count are both 3,489.

| Dossier | Trials | Refused | Effects | Status |
|---|---:|---:|---:|---|
| `LH-X-005` VWRA | 1,160 | 297 | 860 | `no_incremental_information` |
| `LH-X-006` EIMI | 1,160 | 125 | 1,032 | `no_incremental_information` |
| `LH-X-007` EIMI-VWRA | 1,169 | 115 | 1,054 | `inconclusive` |

Each single-name dossier uses the same 29 economic datasets, three transforms, six horizons, and two labels. Stored direction is the sign of the latest change: up is 1, flat is 0, and down is -1. That is not a new cut. Logistic, probit, and regularized search are 9 refusal rows, all `not_estimable_effective_sample`, with null effects. The 26 method rows on each dossier have null effects. `publication_allowed` is false on every trial.

The reverse lookup is `research.etf_protocol_coverage`. It keeps refused rows and null effects. `research.etf_protocol_dossier_summary` is a count view, not a second fact table.

## Registry

`LH-H-005` through `LH-H-007` are category B. The registry result is `no_policy_registered`. No allocation hypothesis was registered. The inspected history is not an uninspected evaluation period.

EIMI is an emerging-market overweight relative to VWRA, not a separate diversifier. Relative outperformance is not treated as a positive absolute return. Detail is in `VWRA.md`, `EIMI.md`, and `PAIR.md`.

Static mixes, periodic rebalancing, and contribution-matched wealth are not simulated. The portfolio path was not built. The 618 catalogue scenarios were not executed. The immediate VWRA contribution path remains the untested default.

Latest-revised macro trials are category B and are not decision inputs. `bea.vintage.real_gdp.pct_preceding` stays a point-in-time indicator and is not a method replay. `macro_vintage_ids` on the three executions is empty.

`LH-H-001` stays `proposed`. `LH-H-002` stays `proposed`. `LH-H-003` stays `retrospective_only` and was not estimated. `LH-H-004` stays `proposed` and was not rescored. This note is not Verified.
