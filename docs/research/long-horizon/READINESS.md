# Long-horizon readiness

**Status:** research record. This is not an investment claim and it is not Verified.

No catalogue family is executed. Seven families stay design-only because a price-only subset was not carved out of the 618 scenarios. Nineteen families are blocked because an input they name is not a stored point-in-time vintage for a registered portfolio method. The discovery coverage matrix is unchanged. There is no foreign-exchange series, no distribution ledger, no ALFRED store, and no replay of a method on `bea.vintage.real_gdp.pct_preceding`.

| Family | Gate | Reason |
| --- | --- | --- |
| Absolute price momentum | design only not executed | Not executed. At least one input is a macro regime. No price-only subset of the 618 scenarios is carved out. |
| Contribution timing policies | design only not executed | Not executed. Cash rates, VIX, and macro regimes are not decision inputs in this package. The pilot calendar is a new specification. |
| Credit & lending | blocked | Blocked. No point-in-time credit vintage is available for a portfolio decision. |
| Cross-macro interactions | blocked | Blocked. The named macro series do not have a vintage that covers a registered portfolio method. |
| Drawdown & dip buying | design only not executed | Not executed. The family mixes prices with CPI, credit, and unemployment inputs. |
| Earnings & profitability | blocked | Blocked. Earnings revisions and profit margins are not stored. |
| FX & currency | blocked | Blocked. No foreign-exchange observations are stored, and the simulator refuses an unsupported conversion. |
| Growth & production | blocked | Blocked. Do not replay a method on bea.vintage.real_gdp.pct_preceding. Other production vintages named here are not stored for a portfolio decision. |
| Inflation & prices | blocked | Blocked. No CPI vintage covers a registered portfolio method. |
| Labour & employment | blocked | Blocked. Latest-revised labour observations are not an execution clock. |
| Liquidity & funding | blocked | Blocked. Funding vintages and a cash-rate series for interest are not stored. |
| Macro methodology outputs | blocked | Blocked. No registered method is point-in-time on its own inputs. Do not replay one on the real GDP growth vintage. |
| Macro plus market confirmation | blocked | Blocked. The macro leg has no eligible point-in-time vintage for a portfolio decision. |
| Market breadth & participation | blocked | Blocked. Constituent breadth is not stored. |
| Market structure and concentration | blocked | Blocked. Historical holdings, NAV, and index weights are not stored. |
| Policy & interest rates | blocked | Blocked. No point-in-time policy-rate vintage is tied to a registered portfolio method. |
| Rates & yield curve | blocked | Blocked. Stored yields are not a point-in-time curve for a portfolio decision. |
| Rebalancing policies | design only not executed | Not executed. Holdings, covariance, and point-in-time regimes are not stored. The pilot rebalance is a separate specification. |
| Regional and structural cycles | blocked | Blocked. Regional vintages, foreign exchange, and total returns are not available. |
| Relative performance & rotation | design only not executed | Not executed. Some scenarios name stored tickers and some require a credit spread or an index that is not a stored listing. |
| Risk control & exposure budgets | blocked | Blocked. Holdings overlap and covariance inputs are not stored. |
| Sequence and lifecycle | design only not executed | Not executed. Income paths are not stored. The pilot does not model a lifecycle. |
| Strategy governance & behavioural | design only not executed | Not executed. This family is a governance checklist. The investment-policy files were not edited. |
| Structural transitions & shocks | blocked | Blocked. Macro releases and a recession chronology are not treated as point-in-time portfolio inputs. |
| Valuation & earnings yield | blocked | Blocked. Earnings and valuation histories are not stored. |
| Volatility & left-tail risk | blocked | Blocked. VIX history beyond the stored adjusted closes is not a licensed input in this package. |

The catalogue portfolio experiment remains `LH-E-001`. It uses stored USD adjusted closes for VWRA and CSPX. It does not use a macroeconomic vintage. Its scientific status is assigned only after the frozen specification is stored and the ledger reconciles. That status is not permission to publish and it is not an investment claim. The outcome-first layer adds `LH-E-002`, a category C frequency study, and `LH-E-003`, a blocked retrospective example. Neither replaces `LH-E-001`.

The stored execution `LH-X-001` reconciled. The predetermined rule assigned `inconclusive`. That status is not an investment claim.

## Laboratory certification, 3 November 2026

This section records a later audit. It leaves `LH-E-001`, `LH-X-001`, `LH-V-001`, and `LH-C-001` in place. No corrected execution was stored. The tolerance is exact decimal equality, which is a difference of zero. `publication_allowed` stays false.

### Portfolio accounting

The passive path and the calendar-split path were rebuilt from the stored USD split-adjusted closes and from the event ledger. Both reconstructions match the stored evidence.

| Path | Terminal wealth | Ending cash | Ending units | Costs | Forgone value |
| --- | --- | --- | --- | --- | --- |
| Immediate VWRA | 150430.016335996 | 187.616335996 | 792 VWRA | 88.723660004 | 0 |
| Calendar split | 155534.402817166 | 27.192817166 | 416 VWRA and 93 CSPX | 100.672404834 | 8726.2 |

There are 89 contributions of 1,000 US dollars, 89,000 in total, on the first common stored session of each month from 2019-07-25 to 2026-11-02. That is 1,838 sessions. The cost rate is 10 basis points of notional. Cash interest is the explicit zero. No distribution and no foreign-exchange conversion is applied. VWRA has no stored close before 2019-07-25.

The figure 8,726.20 is the exact value 8726.2. It is 46 sold VWRA units marked at the 2026-11-02 split-adjusted close of 189.7. Those six sale lots are dated 2020-01-02, 2021-01-04, 2023-01-03, 2024-01-02, 2025-01-02, and 2026-01-02. Terminal wealth is ending cash plus units still held. The forgone mark is a separate field. The wealth gap between the two paths is 5104.386481170. Cent displays of the two terminal-wealth figures are 150,430.02 and 155,534.40. The stored values are the longer decimals above.

The first fill, on 2019-07-25, buys 12 VWRA at 79.925003. Notional is 959.100036, cost is 0.959100036, and residual cash from the 1,000 contribution is 39.940863964. The first January sale, on 2020-01-02, sells 9 VWRA at 86.695. Notional is 780.255 and cost is 0.780255.

A larger calendar-split terminal wealth remains `inconclusive`. The frozen rule is unchanged.

### Passive baselines

These paths use the same contribution dates, the same 1,000 US dollar amount, the same 10 basis point cost, zero cash interest, and the same stored USD split-adjusted closes. A split-adjusted close is a price return. It is a stored adjusted close, and this pass does not certify it as a total return. Holdings lines, exposure snapshots, fund returns, and foreign-exchange rows are zero, so constituent overlap is unsupported.

| Baseline | What the path records | Terminal wealth | Forgone value |
| --- | --- | --- | --- |
| Immediate VWRA | Price path of one listing | 150430.016335996 | 0 |
| Immediate CSPX | Price path of one other listing | 160618.95366197 | 0 |
| Static equal VWRA and CSPX | Fixed mix, buys only | 154623.031399984 | 0 |
| Static 70 percent CSPX | Structural overweight, buys only | 157058.342255089 | 0 |
| Calendar fixed weight | Contribution buys, then a January position rebalance | 155257.058152937 | 379.4 |
| Threshold 10 percent | Rebalance when a weight leaves the band | 155229.120995035 | 189.7 |
| Cash-flow only | Buys toward equal weight, no sales | 155228.850695039 | 0 |

The static CSPX overweight is a structural mix. The calendar fixed-weight path is a different rule from the registered odd-month calendar split. Where a baseline ends above immediate VWRA, the category C rule assigns `inconclusive`. None of these rows is a new hypothesis, a new claim, or macroeconomic investment intelligence.

### Traceability

`research.long_horizon_progress` on the preserved database separates the register from the results. Registered scenarios: 618. Executed simulations: 1. Validated simulations: 1. Scientifically supported conclusions: 0. Candidate rows marked as results: 0. The six dependency rows linking immediate VWRA and the calendar split have `independent_confirmation` false. Shared prices, the same contribution dates, and one overlapping window are one shared history.

### Point-in-time gate

Gate 5 is blocked. 26 registered methods were inspected. Declared vintage classes: latest_revised. This pass does not relabel one. `bea.vintage.real_gdp.pct_preceding` is not a required input of any registered method. The only live provider-vintage dataset on the preserved database is that real GDP growth series. `fred.alfred.UNRATE` historical archiving is prohibited, so ALFRED is not stored. Unemployment, CPI-U, industrial production, and the H.15 Treasury yields are permitted to be archived as their current publications. Those publications are not original vintages. The Employment Situation archive and the CPI archive are also permitted to be archived, and the rights rows say those archived releases may have been revised. No rights-cleared source supplies an original vintage for every input of one registered method. No methodology and no vintage were manufactured.

Gate 6 did not run. There is no macro-informed portfolio experiment in this pass. The 618 catalogue scenarios were not executed.

### Checks

On this tree, not GitHub Actions, and not Verified: `npm run test:research` collected 811 tests, 807 passed and 4 failed. The four failures are the known TradingView rights-fragment tests and the live H.15 count of 868 federal-funds rows where the test expects 867. `uv run ruff check .` passed. `uv run ruff format --check .` would reformat 13 pre-existing files, which were left unchanged. Typecheck, `npm run test:db`, production build, and browser tests were not run.
