# Sahm rule on the short live sample

**Status:** calculated on stored live observations. Not approved for publication.  
**Config:** `sahm_published_v1` (0.50 percentage points).  
**Method:** existing `SAHM_UNEMPLOYMENT_GAP` 1.0.1. The formula was not reimplemented.  
**Run:** `f3db281d-9f6d-4c4c-974f-ba4b9bd68131`. `publication_allowed` is false.

## 1. What this is

This is a short latest-revised calculation on `bls.ln.LNS14000000`. It is not the real-time Sahm series. It is not a decades-long match to `SAHMREALTIME`.

The calculator already in `workers/research/src/aqil_research/methods/sahm.py` applies the published rule: a 0.50 percentage-point rise in the three-month average relative to the prior twelve-month low of that average. The twelve-month look-back excludes the evaluation month. A missing month fails the calculation. The result is a published association with recessions already under way. It is not an NBER determination, not a forward forecast, and not an investment signal.

## 2. Sample

The preserved local research database was reachable. The run used only live `latest_revised` rows.

| Fact | Result |
| --- | --- |
| Live months | 44 |
| First month | 2023-01-01 |
| Last month | 2026-09-01 |
| October 2025 | Absent. Not interpolated. |
| Other gaps inside the live file | None |
| Fixture rows for this dataset | 87 excluded. Not used as a backfill. |

History before 2023-01-01 was not collected for this run.

## 3. Windows

A Sahm window is 15 months. The existing classifier leaves a window invalid when it includes a month that was not collected. October 2025 is that month. The next evaluation month that excludes it is 2027-01-01. Those later observations are not in this file, so no result is reported for them.

| Class | Evaluation months | Count |
| --- | --- | --- |
| Valid | 2024-03-01 through 2025-09-01 | 19 |
| Refused, window includes October 2025 | 2025-10-01 through 2026-09-01 | 12 |
| Refused, earlier months are not in the live file | 2023-01-01 through 2024-02-01 | 14 |

September 2026 is the last stored month and stays refused. An earlier insufficient run, `workflow-e2e-1792616393`, already records `missing months for Sahm calculation: 2025-10-01` for that month. It was not overwritten. `immutability-run-129d829287f7` was also left in place.

September 2025 is the latest month whose window does not need October 2025. It is not a current-month call for the end of the file.

## 4. Indicator values

Threshold 0.50 percentage points. Triggered means the gap is at least 0.50. These nineteen values were produced by the existing calculator. Only the latest valid month was stored as a new run.

| Evaluation month | Three-month average | Prior twelve-month low | Gap | Triggered |
| --- | --- | --- | --- | --- |
| 2024-03-01 | 3.83 | 3.50 | 0.33 | No |
| 2024-04-01 | 3.90 | 3.50 | 0.40 | No |
| 2024-05-01 | 3.90 | 3.50 | 0.40 | No |
| 2024-06-01 | 3.97 | 3.53 | 0.44 | No |
| 2024-07-01 | 4.07 | 3.57 | 0.50 | Yes |
| 2024-08-01 | 4.17 | 3.60 | 0.57 | Yes |
| 2024-09-01 | 4.17 | 3.63 | 0.54 | Yes |
| 2024-10-01 | 4.13 | 3.73 | 0.40 | No |
| 2024-11-01 | 4.13 | 3.73 | 0.40 | No |
| 2024-12-01 | 4.13 | 3.73 | 0.40 | No |
| 2025-01-01 | 4.10 | 3.73 | 0.37 | No |
| 2025-02-01 | 4.10 | 3.80 | 0.30 | No |
| 2025-03-01 | 4.13 | 3.83 | 0.30 | No |
| 2025-04-01 | 4.20 | 3.90 | 0.30 | No |
| 2025-05-01 | 4.23 | 3.90 | 0.33 | No |
| 2025-06-01 | 4.20 | 3.97 | 0.23 | No |
| 2025-07-01 | 4.23 | 4.07 | 0.16 | No |
| 2025-08-01 | 4.23 | 4.10 | 0.13 | No |
| 2025-09-01 | 4.33 | 4.10 | 0.23 | No |

The stored run is September 2025: three-month average 4.33, prior twelve-month low 4.10, gap 0.23, not triggered. The registered calculation also records `threshold_crossed` false. July, August and September 2024 are the only valid months at or above 0.50.

An independent rounding of the stored rates matches the calculator. July 2024 uses 3.9, 4.1 and 4.2 and gives 4.07, 3.57 and 0.50. September 2025 uses 4.3, 4.3 and 4.4 and gives 4.33, 4.10 and 0.23.

## 5. Stored run

| Field | Value |
| --- | --- |
| Run id | `f3db281d-9f6d-4c4c-974f-ba4b9bd68131` |
| Evaluation month | 2025-09-01 |
| Config | `sahm_published_v1` |
| Status | completed, sufficient |
| `publication_allowed` | false |
| Replay | matched before the insert was committed |

The runner is `workers/research/src/aqil_research/workflow/sahm_short_sample.py`. It calls the existing research-run path with collection off, then appends. It does not edit the method registry or the CLI.

## 6. Long-history blocker

A match to the long `SAHMREALTIME` history is blocked. AQ-103 is out of scope. This is a short latest-revised calculation, not the real-time Sahm series, and not a decades-long unemployment history. History before the stored live sample is not backfilled, and October 2025 is not interpolated.

## 7. Tests

`workers/research/tests/test_sahm.py` and `workers/research/tests/test_sahm_window_eligibility.py`: 10 passed. The added test uses calendar dates only and does not invent unemployment observations. `npm run test:research` was not run.
