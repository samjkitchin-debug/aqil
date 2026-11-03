# Long-horizon review

**Status:** research record. This is not an investment claim and it is not Verified.

The freeze commit is `caf498b0149e9dbccecc4477d288fe9bec0bbbaf`. The historical execution was stored after that commit. Reproduction of `LH-X-001` matched status `inconclusive` and artefact `cf77b6fb62f02eaf84828549189893dd7c45aaa49f0470cd6754a27ffa19d514`.

## What the comparison shows

Both ledgers reconcile. Each path receives 89 contributions of 1,000 US dollars. The window is the stored overlap from 2019-07-25 to 2026-11-02, 1,838 sessions. Immediate VWRA ends at 150,430.016335996, of which 187.616335996 is cash and 792 units are VWRA. Costs are 88.723660004. The calendar split ends at 155,534.402817166, of which 27.192817166 is cash, 416 units are VWRA, and 93 units are CSPX. Costs are 100.672404834. Forgone value is 8,726.2 and is not included in terminal wealth. The alternative terminal wealth is larger by 5,104.386481170.

The predetermined rule assigns `inconclusive` when the alternative terminal wealth is larger. A language model did not assign it. The original hypothesis row remains `proposed`. The current status is a later status event. Category C forbids statistical support, economic usefulness, and forward validation. One shared path, with no holdout and with split-adjusted closes rather than total return, is not an investment claim.

## Tests

`npm run test:research` collected 784 tests: 780 passed and 4 failed. The failures are the three TradingView rights-fragment tests and `test_live_board_file_is_counted_in_memory`, which saw 868 federal-funds rows where the test expects 867. Those tests were not changed. The 25 long-horizon tests are inside the 780 passes, including the disposable-database constraint test.

`uv run ruff check .` passed in `workers/research`. `uv run ruff format --check .` would still reformat 13 pre-existing files. Those files were not reformatted. The long-horizon package is not among them.

Not run: `npm run test:db`, TypeScript typecheck, web lint, production build, browser tests, and GitHub Actions. The migration was applied to local Postgres only. It was not applied to a hosted project. The databases were not reset. Live `latest_revised` observations remain 38,653. Adjusted closes remain 42,931. `publication_allowed` remains false on all 54 research runs and on the new execution.

## Certification review, 3 November 2026

This review reads the certification pass. It is a record of that reading. It is not Verified, and it is not an investment claim.

Portfolio accounting. The event replay matches `LH-X-001` exactly. Cash, units, costs, and terminal wealth agree with the fills. Forgone value is 46 sold VWRA units times the final close of 189.7, which is 8726.2, and that product is outside terminal wealth. The first buy and the first January sale match the hand arithmetic in the certification tests. No second execution was required.

Historical data. The prices are stored USD split-adjusted closes. The window starts on the first VWRA session, 2019-07-25. Foreign-exchange rows, holdings lines, and fund-return rows are zero. A split-adjusted close stays a price return.

Traceability. The hypothesis, frozen specification, execution, evidence, and claim still join. The progress view shows 618 registered scenarios, 1 executed simulation, 1 validated simulation, and 0 scientifically supported conclusions. The six dependency rows keep `independent_confirmation` false.

Leakage. The category C pilot has no macroeconomic input. The real GDP growth vintage remains outside every registered method. Every method still declares `latest_revised`. A printed release date is still ineligible on that date. No timestamp was manufactured.

Benchmark fairness. The baselines use the same contributions, cost rate, cash interest, and closes as the pilot. Immediate CSPX and the 70 percent CSPX mix are single-listing and structural results. They are not treated as macro signals.

Inference. One shared price path is one history. A larger terminal wealth stays `inconclusive`. There is no holdout and no second sample.

Reproducibility. `uv run python -m aqil_research.long_horizon.reproduce` returned `LH-X-001` with status `inconclusive` after the certification modules were added. Gate 6 did not run, because Gate 5 produced no eligible method.
