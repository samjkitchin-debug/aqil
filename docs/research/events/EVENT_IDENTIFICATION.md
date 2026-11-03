# Event identification specification

**Status:** frozen research specification, version 1. This is not an investment claim and it is not Verified.

**Definition:** `EVT-DEF-001` version 1.

The thresholds below are preregistered. A change is a new definition version. This document does not report an inventory count. The inventory is a later record and does not rewrite this file.

## Price class

Events use stored split-adjusted closes (`adjusted_close`, adjustment status `adjusted`). A missing session is not filled. Horizons named 1m, 3m, 6m, 12m, 24m, and 36m are stored-session steps of 21, 63, 126, 252, 504, and 756. They are not calendar months.

Each event stays in the stored listing currency. The quote unit must equal that currency. No foreign-exchange rate is applied. No distribution is invented.

VWRA sessions before 2019-07-25 are refused. No earlier VWRA price is manufactured.

## Total return is blocked

Stored series are split-adjusted closes. Distributions are not stored. A split-adjusted close is not relabelled as a total return. The family `total_return_advance` is blocked and has no event rows.

## Labels and signals

An event label may use later stored closes to describe an episode. `usable_as_investment_signal` is false on every catalogue row. The eventual bottom, the rally start, and the forward return are not decision inputs.

A terminal rise of 20 percent that has not been confirmed by a later 20 percent decline is censored. It is not labelled a bull market. An open drawdown of at least 15 percent is censored. It is not labelled a recovery.

## Catalogue rule

Sustained advances and sideways-then-advance episodes keep the earliest qualifying window and resume at its end session. Interiors do not overlap. The shared endpoint may be the next start. Overlapping windows that also qualify are counted and do not each receive an event id.

Negative markets, flat markets, and relative outperformance use a fixed grid. The grid is not a search for the strongest window.

## Sustained advance

The up-session fraction is the share of steps whose close is strictly above the previous close. The minimum up-session fraction is 0.55. The maximum drawdown is the deepest close relative to the running peak inside the window.

| Horizon | Session steps | Minimum return | Maximum drawdown |
| --- | ---: | --- | --- |
| 1m | 21 | 0.05 | 0.08 |
| 3m | 63 | 0.10 | 0.10 |
| 6m | 126 | 0.15 | 0.12 |
| 12m | 252 | 0.20 | 0.15 |
| 24m | 504 | 0.30 | 0.20 |
| 36m | 756 | 0.40 | 0.20 |

## Other price families

| Family | Rule |
| --- | --- |
| Persistent bull | Rise of at least 0.20, confirmed by a later decline of 0.20, lasting at least 126 session steps. |
| Early bull | The first 63 sessions of a persistent bull, and only when that slice ends before the peak. The label uses the later confirmation. |
| Drawdown recovery | Decline of at least 0.15 from a peak, then the first later close at or above that peak. |
| Early recovery | Inside a completed recovery, the earlier of 63 sessions and a retracement of 0.50, strictly before the full recovery. |
| Sideways then advance | 126 sideways sessions with absolute return at most 0.08, range at most 0.12 of the start, and drawdown at most 0.10, then a 63-session advance of at least 0.10. |
| Relative outperformance | Fixed 252-session grid. Excess of at least 0.10 over the median of at least 3 other US-dollar listings. Peer sessions must fall on the end date or within the previous 5 calendar days. |
| Leadership transition | Last stored US-dollar session of each calendar month. A new leader must lead by at least 0.05. At least 3 listings must be eligible. Ties use alphabetical ticker. The spread uses closes on or before the month-end and is still not a signal. |
| Failed rally | An attempt rise of 0.08 that falls by 0.08 back to or below its trough before the rise reaches 0.15. |
| Negative market | Fixed 126-session grid from the first session. Return below 0, unless the flat band applies. |
| Flat market | The same grid. Absolute return at most 0.03, and this band is classified before negative. |

Cross-currency relative performance and leadership are blocked. EUNA is euro-denominated, and no conversion is applied.

## Rally despite deterioration is blocked

No registered deterioration rule has an original vintage. Latest-revised macro observations are not used to label a rally. `bea.vintage.real_gdp.pct_preceding` does not unlock a method. The family `rally_despite_deterioration` is blocked and has no event rows.

## What this specification does not do

It does not execute the 618 catalogue scenarios. It does not rewrite `LH-H-001`, `LH-E-001`, `LH-X-001`, or the 960-cell coverage matrix. It does not authorise publication. `publication_allowed` stays false.
