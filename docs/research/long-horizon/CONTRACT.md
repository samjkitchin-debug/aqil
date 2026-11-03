# Long-horizon scientific contract

**Status:** research record. This is not an investment claim and it is not Verified.

## Linked records

A hypothesis, an experiment specification, an execution, an evidence record, and a claim are separate rows and can be joined.

- The original proposition is version 1. A later version is a new row. Version 1 is not updated.
- An execution is immutable. A re-run is a new execution id. This package stores one execution, `LH-X-001`.
- Evidence keeps the decision path, fills, cash, units, wealth, and forgone lots. A rejected comparison keeps its evidence.
- The current scientific status is the latest row in `research.scientific_status_events`. It does not replace the evidence.
- Shared inputs and overlapping periods are rows in `research.research_dependencies` with `independent_confirmation` false. They are not independent confirmations.
- `publication_allowed` stays false. Nothing in this package grants publication.

## Categories

| Category | Label | Meaning in this package |
| --- | --- | --- |
| A | historically valid point-in-time | An investment experiment that could have been decided with information available at the decision. None is registered here. |
| B | retrospective economic research | A later description of an economy. It is not relabelled as a point-in-time investment result. None is registered here. |
| C | price-only simulator research | Accounting on stored listing-currency prices. The pilot is category C. It is not macroeconomic investment intelligence. |

Macro-informed portfolio simulation stays blocked until a vintage covers a registered method's own inputs. The real GDP growth vintage is not replayed as a portfolio method. ALFRED is not stored.

## Next eligible session

Before a BEA vintage is used in a decision, the printed release date is not eligible on that calendar date, even when that date is a stored session. The first eligible session is the next stored session strictly after the printed date. If no later session is stored, the decision is blocked. A session is not invented. Midnight UTC remains an identity anchor, not an observed publication time. The existing observation-availability selector is unchanged. The category C pilot does not use this series, so the pilot does not apply the rule.

## Simulator

Synthetic cases with known cash, units, costs, and terminal wealth pass before the historical comparison. The engine uses `Decimal`. It buys and sells whole units and leaves residual cash. Costs are explicit. A sale keeps the sold units on a forgone path, marked to the later price, and that value is not portfolio wealth. Cash interest must be an explicit rate. Distributions are refused. A missing session is refused. A currency conversion is refused, because no foreign-exchange rate is stored. Synthetic tests do not support an investment-performance claim. `supports_investment_alpha()` is false.

## One comparison

The frozen specification is `LH-E-001` for hypothesis `LH-H-001`. The passive policy invests each contribution in VWRA. The alternative buys VWRA in odd months, CSPX in even months, and on a January contribution session rebalances the two holdings toward equal value after that contribution. Both use the same contribution dates and the same amount. The window is the overlap of stored adjusted closes, starting at the later listing. No price is manufactured before a stored session.

The status rule is fixed before the historical result is read:

- an unreconciled ledger is `insufficient_data`;
- a larger alternative terminal wealth is `inconclusive`;
- an equal or smaller alternative terminal wealth is `rejected` on this window only.

`statistically_supported`, `economically_useful`, and `forward_validated` are forbidden for category C. The sentence of the claim is filled from that rule. A language model does not assign the status. The result is not promoted to an investment claim.
