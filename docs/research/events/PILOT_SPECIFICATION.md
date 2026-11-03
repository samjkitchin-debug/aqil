# Pilot intersection specification

**Status:** frozen before the intersection is scored. This is not an investment claim and it is not Verified.

**Hypothesis:** `LH-H-002` version 1. **Experiment:** `LH-E-002` version 1. The experiment is category C price-only research. It is not macroeconomic investment intelligence.

The hypothesis is not one of the 618 catalogue scenarios. `LH-X-001` is not reopened. No portfolio comparison is run.

## The conjunction

Both legs must be true. There is no composite score and there are no weights.

1. Completed drawdown, observable from closes on or before the decision session. The lookback is 252 stored sessions. The peak is the earliest maximum in that window. The trough is the minimum after that peak and on or before the decision. The decline is at least 0.10. The decision close is at least 0.05 above the trough.
2. Price momentum. The 63-session price return ending on the decision session is at least 0.05.

The two legs can describe one price path. They are not treated as independent economic facts.

## The outcome label

A labelled advance is a 126-session price return of at least 0.10. The label uses a later close. It is not known at the decision and it is not a signal. It is not the inventory sustained-advance filter, which also requires a path limit and a higher 6-month threshold of 0.15.

## The comparison grid

Decision dates are the last stored session of each calendar month, for each listing, when 252 prior sessions and 126 later sessions exist. A month without that span is excluded because the label cannot be computed. Exclusion does not use the sign of the later return.

Every eligible month-end is kept. Months in which the conjunction is false are the controls. `selected_on_future_return` is false. Those controls are the matched non-event periods.

## Status rule

A symbol qualifies only with at least 12 eligible months, 3 condition months, and 3 labelled advances. Fewer than five qualifying symbols is `insufficient_data`.

Otherwise the medians across qualifying symbols decide the status. An odd count uses the middle value. An even count uses the mean of the two middle values.

- Rejected when the median lift is not positive.
- Rejected when the median condition frequency is at least 0.40. The condition is then common in ordinary eligible months.
- Rejected when the median share of labelled advances preceded by the condition is at least 0.70. The condition then accompanies most labelled advances.
- Otherwise `inconclusive`.

`statistically_supported`, `economically_useful`, and `forward_validated` are forbidden.

There is no separate training window and no separate validation window. The eligible month-ends are the only sample. That sample is inspected by this experiment. It is not an untouched holdout.

## Portfolio comparison

The portfolio comparison is blocked. This experiment does not call the simulator. A larger alternative terminal wealth would be inconclusive under the `LH-E-001` rule. A later portfolio test would be a new experiment id.

## Retrospective macro intersection

`LH-H-003` and `LH-E-003` are category B. The example conjunction is improving industrial production (`fed.g17.IP.B50001.S`), declining consumer prices (`bls.cu.CUSR0000SA0`), and positive equity momentum. It is not estimated. No observation values are read for it. No weights are defined. Latest-revised series are not a decision clock. `bea.vintage.real_gdp.pct_preceding` is not an input. ALFRED is not stored. The portfolio path is blocked.

## Publication

`publication_allowed` stays false.
