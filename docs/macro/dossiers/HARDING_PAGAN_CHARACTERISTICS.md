# Harding–Pagan characteristics

**Status:** implemented on stored latest-revised levels. Publication is not approved. Operational acceptance is not claimed.
**Method id:** `HARDING_PAGAN_CHARACTERISTICS`.
**Dating:** existing `date_spencer15_variant`. Quarterly BBQ is not implemented.
**Stored run:** `0d667a12-5a9c-45e0-b04a-8aea4196bc19` on local `postgres`, 30 October 2026. `publication_allowed` is false.

## 1. Identity

Harding and Pagan, "Dissecting the cycle", *Journal of Monetary Economics*, 2002, describe phase duration, amplitude, and a concordance index. This note uses those characteristics. It does not implement their quarterly BBQ rule, and it does not run BBQ on monthly industrial production.

Turning points come from `BRY_BOSCHAN_SPENCER15_VARIANT`. There is no second monthly dating engine.

## 2. Phase rule

After a trough, and up to the next peak, the phase is expansion. After a peak, and up to the next trough, the phase is contraction. The peak month is the last month of expansion. The trough month is the last month of contraction. Months before the first turn and after the last turn are unclassified.

If the turns do not alternate, phases are not forced.

## 3. Duration and amplitude

Duration is the number of months from the month after one turn through the next turn. That count is the gap in months between the two dates.

Amplitude is the percent change in the level between those two dates: later level minus earlier level, divided by the earlier level, times 100. The stored percent is rounded half up to four decimal places. A starting level of zero leaves the percent undefined.

## 4. Concordance

Concordance is the Harding–Pagan index: the share of compared months in which both series are in expansion or both are in contraction. The denominator is the number of months where both series have a classified phase. Unclassified months are left out of the share. The stored share is rounded half up to six decimal places, and the integer counts are stored with it.

## 5. Inputs and eligibility

Each series is dated on its own level, and only when it passes the same structural rules the Spencer-15 kernel already requires for a level input: a live retrieval, the series' own level unit, seasonal adjustment already applied, monthly frequency, `latest_revised`, an observed value, a month start, a finite value, no duplicate month, and no gap. A gap is not filled. A growth rate is not dated. A series that fails is recorded and is not given a turning point.

The four series are:

| Series | Dataset | Level unit | Eligible sample in the stored run |
| --- | --- | --- | --- |
| Industrial production | `fed.g17.IP.B50001.S` | `index_2017_100` | 1919-01-01 to 2026-09-01, 1,293 months |
| Real personal income excluding transfers | `bea.nipa.T20600.W875RX` | `millions_chained_2017_dollars` | 1959-01-01 to 2026-08-01, 812 months |
| Real manufacturing and trade sales | `bea.nipa.U002BU.KPMT` | `millions_chained_2017_dollars` | 1997-01-01 to 2026-07-01, 355 months |
| Total nonfarm payroll employment | `bls.ce.CES0000000001` | `thousands` | 1939-01-01 to 2026-09-01, 1,053 months |

All four were eligible on the stored latest-revised file. G.17 uses `assess_g17_level_input` unchanged. The other three use the same checks with their own dataset id and level unit.

## 6. Chronology and revision limit

The dates are `retrospective_full_sample` and `latest_revised`. The Spencer smoother is centred, so these dates are not a contemporaneous recession call. Revision sensitivity is blocked because the inputs are `latest_revised`. No vintage panel was invented.

These are specific-cycle phases in each series. Payroll, income, and sales turns are not NBER recession dates. Industrial production turns are not the NBER reference chronology either.

## 7. Stored counts

`publication_allowed` is false. Recomputing the run with the characteristics registry matched the stored calculation. The default method registry does not yet contain this method; registration is left to the integrator.

| Series | Peaks | Troughs | Phases |
| --- | --- | --- | --- |
| Industrial production | 18 | 19 | 36 |
| Real personal income excluding transfers | 6 | 6 | 11 |
| Real manufacturing and trade sales | 3 | 3 | 5 |
| Total nonfarm payroll employment | 11 | 11 | 21 |

The industrial production peak and trough counts match Spencer-15 run `3955f7f4-08f8-4e7b-9ded-b3f6eea6633f`, which itself matches the peak and trough lists of run `8fb20325-414f-401b-8c46-bda82ed94e16`.

Pairwise concordance, as the share of months in the same phase:

| Pair | Same phase | Compared months | Concordance |
| --- | --- | --- | --- |
| Industrial production and income | 494 | 583 | 0.847341 |
| Industrial production and sales | 205 | 235 | 0.872340 |
| Industrial production and payroll employment | 699 | 795 | 0.879245 |
| Income and sales | 198 | 235 | 0.842553 |
| Income and payroll employment | 370 | 435 | 0.850575 |
| Sales and payroll employment | 75 | 113 | 0.663717 |

The sales comparisons use fewer months because that series starts in January 1997 and its classified phases are shorter. A lower concordance is a description of those phases. It is not a confirmation, or a rejection, of an NBER recession.

## 8. What this run does not claim

Quarterly BBQ was not implemented and was not run on monthly G.17. No series was described as an NBER recession. The run is not approved for publication. It is not an operational acceptance. `npm run test:research` was not run for this note.
