# Monthly Bry–Boschan turning-point procedure

**Status:** specification blocked. Dating code was not written.  
**Role:** engineering-validation pilot. Not the first strategic intelligence capability.  
**Priority:** P0, implementation rank 1.  
**Backlog:** AQ-094 through AQ-100.  
**Last source check:** 25 October 2026, NBER chapter PDF `c2148` (58 pages), including the appendix.  
**Campaign A classification:** blocked. The input contract was tested. The turning-point procedure was not implemented, because the Spencer coefficients are not in the chapter.

## 1. Identity and provenance

Gerhard Bry and Charlotte Boschan, *Cyclical Analysis of Time Series: Selected Procedures and Computer Programs*, NBER, 1971. ISBN 0-87014-223-2. Chapter 2, "Programmed Selection of Cyclical Turning Points", chapter URL recorded by NBER as `http://www.nber.org/chapters/c2148`. PDF read: `https://www.nber.org/system/files/chapters/c2148/c2148.pdf`.

The chapter is the programming of the NBER practice in Burns and Mitchell, *Measuring Business Cycles* (1946), which the chapter cites. It is a book chapter, not a later journal replication.

Harding and Pagan, "Dissecting the cycle", *Journal of Monetary Economics*, 2002, DOI `10.1016/S0304-3932(01)00108-8`, is a **quarterly** analogue. Their 1999 Melbourne Institute working paper No. 13/99 describes the quarterly rule and was read. The journal text was not line-checked. Quarterly BBQ is documented in section 3 as a different method. It is not this pilot.

## 2. Original economic purpose

The chapter dates specific-cycle peaks and troughs in a single seasonally adjusted series so that expansions and contractions can be measured with less discretion than a freehand reading. It is classificatory and descriptive. It does not estimate a probability, a forecast, or a causal effect. It does not define the NBER reference cycle. The reference cycle is an external chronology produced by the NBER's committee procedures.

## 3. Mathematical specification

The following is taken from chapter 2 as read on 25 October 2026 from `https://www.nber.org/system/files/chapters/c2148/c2148.pdf`. The PDF is 58 pages. The appendix is a sample run for bituminous-coal production (output tables), not a program listing. No FORTRAN listing is in this file. Where the principles prose and Table 1 disagree, Table 1 is the programmed procedure and the disagreement is named in the frozen card. A constant that the PDF does not print is not supplied from later software.

The procedure looks for swings of business-cycle length: longer than fifteen months and shorter than twelve years from trough to trough or peak to peak. The worked example is seasonally adjusted bituminous-coal production.

Steps stated in the chapter:

1. Extreme values are identified against a preliminary unadjusted Spencer curve. The exclusion criterion stated for that example is 3.5 standard deviations of the ratios to that curve. Extremes are replaced by the Spencer-curve value for later smoothed curves. The chapter says an extreme can still be chosen as a final turning point.
2. On the twelve-month moving average of the extreme-adjusted series, a tentative peak is a month higher than the five months on either side. A tentative trough is lower than the five months on either side. Contiguous like turns are reduced by keeping the highest peak, or the latest if equal, and the analogous rule for troughs.
3. Spencer-curve turns are the highest or lowest point within five months of those twelve-month-average turns. Like turns must be at least fifteen months apart. Alternation is enforced. Turns within six months of the ends of the series are rejected. If a twelve-month-average contraction is shorter than ten months, overlapping searches that would invert the order of the Spencer peak and trough cause both turns to be dropped.
4. A short moving average, the MCD curve, is searched within five months of the Spencer turns. MCD is months for cyclical dominance, confined to a three-to-six-month smoother: three months when MCD is one or two, six months when MCD is seven or more. The same duration, endpoint, and crossover tests apply.
5. Final turns are the highest or lowest unsmoothed observations within a span of plus or minus MCD months, or four months, whichever is longer, around the MCD turns. Turns closer than six months to the ends are rejected. The first and last peak or trough must be at least as extreme as any value between it and the end of the series.
6. Full cycles, peak to peak and trough to trough, must last at least fifteen months. Phases must last at least five months. The chapter says the five-month phase rule was not part of standard NBER practice and was added because strikes could be smoothed into false cycles. It also says the rule could be changed if experience showed it was inadequate. The program listing is not in the chapter PDF, so the five-month prose rule stands and was not replaced.

Harding–Pagan quarterly BBQ, from the 1999 working paper: a local peak relative to two quarters on either side, then censoring of phase and cycle length. That paper discusses a four- or five-quarter minimum cycle in its empirical section. Software defaults of a five-quarter cycle and a two-quarter phase appear in later code documentation and were **not** treated as the journal's specification. Do not run that quarterly rule on monthly G.17. Do not "adapt" it by setting the window to five months and calling the result Bry–Boschan. The monthly procedure's smoothing sequence is part of the method. Quarterly BBQ is not a parameter of `BRY_BOSCHAN_MONTHLY_1971`.

### Frozen card, `BRY_BOSCHAN_MONTHLY_1971`

Read from the chapter PDF on 25 October 2026. The same constants are in `workers/research/src/aqil_research/methods/bry_boschan_monthly.py`. `publication_allowed` is false. The method is not registered, because dating is refused.

| Constant | What the chapter prints | Decision |
| --- | --- | --- |
| Spencer fifteen-point weights | Footnote 7 calls it a weighted moving average with the highest weights in the centre and negative weights at the ends. The suggestions section calls it a graduated 15-point weight pattern. No coefficient and no divisor are printed. | Blocker. Not copied from any other program. |
| Program listing | Absent. The appendix is Output Tables for bituminous coal, including the printed control limit 3.500. | Prose and Table 1 govern. They cannot supply the missing weights. |
| Outlier rule | Ratios to the preliminary unadjusted Spencer curve A. Control limit 3.5 standard deviations of those ratios, printed as 3.500. The coal output records a mean ratio of 99.99 and a standard deviation of 7.853. Extremes are replaced by the Spencer A value on later smoothed curves. An extreme may still be a final turn. | Frozen as 3.5. The replacement value still depends on the missing weights. |
| Twelve-month moving-average alignment | The chapter does not say centred, trailing, or a two-by-twelve average, and it does not say which month receives an even-length average. | Blocker. The garbled sample table was not used to infer an alignment. |
| Spencer alignment | Highest weights in the centre, so the filter is centred once the weights exist. | Not usable without the coefficients. |
| Windows of five months | A twelve-month-average peak is higher than the five months on either side, and a trough is lower. Spencer and MCD turns are the highest or lowest value within plus or minus five months of the previous curve's like turn. | Frozen. |
| MCD span | The smoother is three to six months: three when measured MCD is one or two, six when measured MCD is seven or more. The coal example is four. Footnote 11 defines MCD as the span at which the average irregular change becomes smaller than the average trend-cycle change, and cites Shiskin (1960). The chapter does not specify that decomposition. | The three-to-six cap is frozen. The measurement formula is not operational from this chapter. |
| Final neighbourhood | Plus or minus the MCD term, or four months, whichever is longer, on the unsmoothed series. | Frozen as a rule. It cannot be applied until MCD is measured. |
| Cycle length | Table 1 censors full cycles shorter than fifteen months. The principles section also says swings shorter than twelve years. Table 1 does not contain that ceiling. | Chosen reference: Table 1. The twelve-year sentence is not added as a silent extra censor. |
| Phase length | Five months. Added by the program; not standard NBER practice. | Frozen at five months. |
| Endpoint ban | Table 1 drops turns within six months of either end of the unsmoothed series. The Spencer section also refuses a turn within six months of the end, and the coal run reports a first turn too near the beginning. | Frozen at six months. |
| Tie break | Contiguous twelve-month-average peaks: keep the highest, and the latest if the values are equal. The analogous rule applies to troughs. | Frozen. |
| Alternation | Enforced. A like turn dropped for the fifteen-month rule requires an opposite turn to be dropped as well. | Frozen as an order: reduce contiguous like turns on the twelve-month average first; on the Spencer curve, drop the lower peak or the higher trough, then restore alternation. |
| Crossover | A twelve-month-average contraction shorter than ten months can make the Spencer searches overlap. If that would put the trough before the peak, both turns are dropped. The MCD step repeats the duration, endpoint, and crossover tests. | Frozen. |
| Quarterly Harding–Pagan BBQ | Not in chapter 2. | Not a parameter. |

`date_specific_cycles` raises `BryBoschanSpecificationBlocked` and returns no dates. No G.17 peaks or troughs were produced.

## 4. Input data

One seasonally adjusted monthly series. The pilot series is `fed.g17.IP.B50001.S`, Federal Reserve G.17 total industrial production index. A read-only recount on local `postgres` on 25 October 2026, after the specification stop and before any dating code, found 1,293 rows. All 1,293 are `latest_revised`, `live`, monthly, seasonally adjusted, unit `index_2017_100`, and numerically finite. There were 0 fixture rows, 0 replay rows, 0 duplicate months, and 0 missing months from 1919-01-01 to 2026-09-01. The hosted project was not queried. This is not a GitHub Actions result.

The chapter assumes seasonal adjustment has already been done. Aqil must not seasonally adjust this index again. Missing months fail the run. The series is revised data, not a vintage panel. No transformation to growth rates is part of the classical procedure described in the chapter. Growth-cycle dating, which the book also discusses, is out of scope.

## 5. Outputs

Dated peaks and troughs on the original monthly index, plus the phase and cycle lengths implied by those dates. No probability, no index level, and no statement that the US economy is in recession. A specific cycle in industrial production is not the NBER reference cycle.

## 6. Estimation

Rule-based. No estimated parameters. The MCD span is a property of the series under the chapter's definition, not a fitted regression coefficient. Re-estimation does not apply. A code or constant change is a new implementation version.

## 7. Institutional implementations

The NBER used programmed selection as a check on its own dating of specific cycles. The chapter compares program dates with Burns–Mitchell dates for a *Business Cycle Developments* sample and reports discrepancies, including a 1934 coal-production episode. Later quarterly practice is Harding–Pagan, not a monthly redefinition. Public code exists that claims to implement Bry–Boschan. It is not an authority until AQ-094 shows it matches the chapter. It may be used as an independent numerical reference only after that check.

## 8. Empirical validation

The chapter's own check is agreement with previously selected NBER specific-cycle dates on 51 indicators, with stated discrepancies. That is a diagnostic of the procedure against an earlier judgement, not a proof of investment value. The sample is biased toward series that already had recognisable cycles. The chapter says so.

Aqil's historical check is the same kind of diagnostic against the NBER **reference** chronology, which is a different object from specific-cycle dates. Disagreement is expected and is not a failure.

## 9. Failure modes

Smoothing can move or invent short contractions, as the chapter's 1934 coal example shows. Extreme values and strikes can become turning points. Endpoint rules leave the latest months undated. A revised industrial-production history can move past dates. The procedure has no sampling error of the regression kind, but the censoring constants are judgement. Applying quarterly BBQ windows to monthly data would date a different object. Latest-revised data are not what an analyst would have seen in real time.

## 10. Aqil applicability

The pilot proves the engineering lifecycle on a long series Aqil already holds. It does not answer whether the US economy is currently in a reference-cycle recession. Later factor and nowcast models can use these specific-cycle dates only as a labelled retrospective diagnostic, not as a training label known in real time.

## 11. Data readiness

Ready for a retrospective pilot. See `docs/macro/DATA_DEPENDENCIES.md`. No acquisition. Rights for G.17 are already operational. Vintages are absent.

## 12. Engineering requirements

Pure Python is the default. No numerical library was added. Dating is not in the registry. Storage would be one `research.research_runs` row per evaluation once a chapter-complete procedure exists. The worker has no cron and no job queue. No recurring entry point was added, because there is no dating result to refresh.

## 13. Validation plan

Numerical acceptance is a fixture series with known dates produced by the frozen procedure, plus a second implementation or a worked chapter example if the coal-production output tables can be transcribed. It is not an exact match to NBER reference dates.

The NBER chronology is loaded as an external dated list, with the date of the chronology file recorded. The report counts agreements and misses. It does not set a minimum overlap.

Robustness that is in scope after the base procedure passes: the effect of the five-month phase rule, and the effect of dropping the latest six months. Changing those constants is a new version, not a silent tweak.

## 14. Operational acceptance

- **Implemented:** the frozen card's steps pass the fixtures.
- **Historically validated:** the NBER diagnostic has been written and does not pretend to be a real-time test. There is no overlap threshold.
- **Recurring:** a new or revised G.17 month produces a new run or an explicit unchanged result, idempotently.
- **Operational:** monitoring for this run is on, replay matches, and `publication_allowed` is still false. Operational here means the pilot machinery is safe to keep running. It does not mean the dates are a business-cycle call.
- **Suspend** if replay fails, censoring rules are breached, or the input series is incomplete.

## 15. Campaign A classification

Blocked, on the evidence of this session. Commands actually run:

- Read-only SQL on local `postgres` as `research_worker`, `default_transaction_read_only = on`. Result: 1,293 live `latest_revised` G.17 months, 1919-01-01 to 2026-09-01, no gaps, no fixture rows.
- `uv run pytest tests/test_bry_boschan_monthly.py -q` in `workers/research`: 9 passed. The tests cover a contiguous level sample, a gap, a fixture retrieval, a growth-rate representation, a non-level unit, a series that is not seasonally adjusted, a non-finite value, and the refusal to date.
- `uv run ruff check` and `uv run ruff format` on the new module and test: clean after format.

No research run was stored. There is no run id and no peak or trough list. Replay, recalculation, monitoring, and the NBER overlap diagnostic were not started, because they require dates from the blocked procedure. Unattended scheduling was not added. `publication_allowed` remains false.

## 16. Status and priority

AQ-094 records the readable constants and the two blockers that stop dating: the Spencer coefficients, and the twelve-month moving-average alignment. The MCD measurement formula is also not operational from this chapter. AQ-095 recount matches the earlier local count. AQ-096 through AQ-100 stay blocked on those unread constants. The strategic milestone remains `STOCK_WATSON_DFM`.
