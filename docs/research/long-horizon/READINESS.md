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

The only registered experiment is the category C pilot `LH-E-001`. It uses stored USD adjusted closes for VWRA and CSPX. It does not use a macroeconomic vintage. Its scientific status is assigned only after the frozen specification is stored and the ledger reconciles. That status is not permission to publish and it is not an investment claim.
