# Lead-lag cross-correlations

**Status:** implemented on stored latest-revised levels. Publication is not approved. Operational acceptance is not claimed.
**Method id:** `LEAD_LAG_CROSS_CORRELATION`, version `0.1.0`.
**Stored run:** `94152391-c3a8-48d7-8f2e-8c4d1dfdb811` on local `postgres`, 30 October 2026. `publication_allowed` is false.

## 1. Identity

This note reports historical cross-correlations among four coincident growth rates. Historical correlation is not a structural lead. No series is assigned a fixed leading-indicator status.

## 2. Transformation and sample

The transformation is monthly natural log-growth, not a three-month change. Monthly log-growth matches the industrial-production autoregressive benchmark and does not add the overlap of a three-month change.

The series, on `latest_revised` levels, are:

| Series | Dataset | Level unit |
| --- | --- | --- |
| Industrial production | `fed.g17.IP.B50001.S` | `index_2017_100` |
| Real personal income excluding transfers | `bea.nipa.T20600.W875RX` | `millions_chained_2017_dollars` |
| Real manufacturing and trade sales | `bea.nipa.U002BU.KPMT` | `millions_chained_2017_dollars` |
| Total nonfarm payroll employment | `bls.ce.CES0000000001` | `thousands` |

The balanced overlap is February 1997 to July 2026, 354 growth months. No overlap month was left outside that contiguous run.

## 3. Sign convention and standard errors

Positive lag means the second series lags the first. Lag 0 is contemporaneous. A correlation at lag +1 aligns the second series one month after the first. That alignment is not a structural lead.

Lags run from -12 to +12. Significance uses Bartlett standard errors. The variance factor is the sum of the product of the two autocorrelation functions, from lag 0 through the predeclared truncation of 24, with the negative lags folded in. The sample size in the standard error is the number of paired months at that lag. A correlation is distinguishable from zero only when its absolute value exceeds 1.96 of those standard errors.

Independent-and-identical standard errors are not used. If the Bartlett variance estimate is not positive, the lag is not called distinguishable from zero.

## 4. Full-sample peaks

On the balanced sample, 30 lag correlations are distinguishable from zero. In every pair the strongest absolute correlation is contemporaneous, and each of those six is distinguishable from zero.

| First series | Second series | Lag | Correlation | Bartlett standard error |
| --- | --- | --- | --- | --- |
| Industrial production | Real personal income excluding transfers | 0 | 0.540568 | 0.055262 |
| Industrial production | Real manufacturing and trade sales | 0 | 0.737681 | 0.056181 |
| Industrial production | Total nonfarm payroll employment | 0 | 0.788936 | 0.054529 |
| Real personal income excluding transfers | Real manufacturing and trade sales | 0 | 0.502251 | 0.054124 |
| Real personal income excluding transfers | Total nonfarm payroll employment | 0 | 0.574877 | 0.054350 |
| Real manufacturing and trade sales | Total nonfarm payroll employment | 0 | 0.679429 | 0.054495 |

Other distinguishable lags, with the same sign convention, are stored on the run. They include, for industrial production and payroll employment, lag -2 at -0.230148 and lag +1 at 0.183571. Those are historical correlations. They do not assign payroll employment, or any other series, a fixed leading-indicator status.

## 5. Subsample stability

The illustrated break left out of both windows is January 2008 through December 2009. The windows do not overlap each other.

| Window | Growth months | Status |
| --- | --- | --- |
| 1997-01 through 2007-12 | 131 | Computed |
| 2010-01 through 2019-12 | 120 | Computed |

Neither window was skipped. The minimum length is 60 growth months.

A pair is recorded as stable only when both windows are computed, each strongest absolute correlation is distinguishable from zero, the lags match, and the signs match. None of the six pairs is stable. The strongest lag in the early window is not the strongest lag in the later window. In the later window, the strongest correlation for industrial production and income (lag 5, 0.174613) and for sales and payroll employment (lag -10, 0.182440) is not distinguishable from zero after the Bartlett standard error.

| Pair | Early strongest lag | Later strongest lag | Stable |
| --- | --- | --- | --- |
| Industrial production and income | -9 | 5 | No |
| Industrial production and sales | 0 | -4 | No |
| Industrial production and payroll employment | 0 | -11 | No |
| Income and sales | -9 | 4 | No |
| Income and payroll employment | -2 | 11 | No |
| Sales and payroll employment | 7 | -10 | No |

Agreement would still not be a structural lead. Disagreement means the full-sample contemporaneous peak is not repeated as the strongest absolute correlation in both windows.

## 6. Registration

`LeadLagCrossCorrelationMethod` is registered in `default_method_registry`. `refresh.py` is unchanged because this is a full-sample estimate, not an idempotent single-series refresh:

```python
from aqil_research.methods.lead_lag import LeadLagCrossCorrelationMethod

registry.register(LeadLagCrossCorrelationMethod())
```

## 7. What this run does not claim

Historical correlation is not a structural lead. No series is a fixed leading indicator. The path is `latest_revised`, not a real-time vintage. `publication_allowed` is false. The run is not an operational acceptance. `npm run test:research` was not run for this note.
