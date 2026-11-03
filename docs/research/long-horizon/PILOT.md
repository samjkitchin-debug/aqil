# Category C pilot

**Status:** research record. This is not an investment claim and it is not Verified.

Hypothesis `LH-H-001`, experiment `LH-E-001`, execution `LH-X-001`.
Evidence `LH-V-001`, claim `LH-C-001`.

The specification was frozen before this run. Category C is price-only simulator research. It is not macroeconomic investment intelligence. `publication_allowed` is false.

## Reconciliation

Both ledgers reconcile. Contributions match. Whole units and residual cash are explicit. Costs are 10 basis points of notional. Cash interest is the explicit zero. No distribution and no foreign-exchange conversion were invented.

| Path | Terminal wealth | Ending cash | Ending units | Costs | Forgone value |
| --- | --- | --- | --- | --- | --- |
| Immediate VWRA | 150430.016335996 | 187.616335996 | {'VWRA': 792} | 88.723660004 | 0 |
| Calendar split | 155534.402817166 | 27.192817166 | {'VWRA': 416, 'CSPX': 93} | 100.672404834 | 8726.2 |

Window `2019-07-25` to `2026-11-02`, 1838 common stored sessions, 89 contributions of 1000 US dollars.
The window starts at the later stored close. No VWRA history was manufactured before the first stored session.

## Scientific status

The predetermined rule assigns `inconclusive`. A language model did not assign it. A larger alternative terminal wealth would still be inconclusive.
Statistical support, economic usefulness, and forward validation are forbidden for this category. The full decision and wealth path is in `research.evidence_records`.

Specification hash `50cdcdb1bf00ee04af6dd09ecff8c4c1dd19df562d8032bbdd79e3ac17b1ac54`.
Artifact hash `cf77b6fb62f02eaf84828549189893dd7c45aaa49f0470cd6754a27ffa19d514`.
Price-series hash `947e5c247b9641e646b05e7cc08d951fcd4d3da8c75074ae893280b73e94559b`.
Code hash `a3055ec537c2028d32719cf1e0efca29682ae365c447fde963fe6e7f92ef8e51`.
Git commit `caf498b0149e9dbccecc4477d288fe9bec0bbbaf`.

Reproduce with `uv run python -m aqil_research.long_horizon.reproduce` from `workers/research` after the local databases are available. The stored prices are not copied into Git.
