# Autoregressive benchmark

**Status:** implemented on stored latest-revised levels. Publication is not approved. Operational acceptance is not claimed.
**Method id:** `AUTOREGRESSIVE_BENCHMARK`, version `0.1.0`.
**Series:** `fed.g17.IP.B50001.S` only.
**Stored run:** `7c33c9b1-3759-4fa6-86ea-c0bcbc86257e` on local `postgres`, 30 October 2026. `publication_allowed` is false.

## 1. Identity

This is a validation baseline for one autoregression. It is not a product forecast. A better in-sample fit is not forecast skill.

The modelled series is the monthly natural log-growth of industrial production: the natural log of one month minus the natural log of the previous month. The level unit is `index_2017_100`. The input is `latest_revised`. The log-growth is not differenced again, whether or not the stationarity check rejects a unit root.

## 2. Predeclared design

| Choice | Value |
| --- | --- |
| Maximum lag | 12 |
| Lag criterion | AIC on a common sample that starts after lag 12. A tie keeps the smaller lag. |
| Minimum estimation length | 120 growth months |
| Window | Expanding |
| Horizons | 1 and 12 months |
| Benchmark | Arithmetic mean of that same origin's estimation window |
| Residual check | Ljung-Box at lag 24, with degrees of freedom reduced by the selected lag |
| Stationarity check | Augmented Dickey-Fuller, constant, automatic lag by AIC up to 12 |
| Full-sample standardisation | Not used |
| Beat rule | Both mean absolute error and root mean squared error must be strictly lower |

Each rolling origin selects its own lag from that window only. The full-sample lag is not reused for those forecasts. There is no look-ahead in the scores.

The autoregressive polynomial is not constrained to be stationary. An in-sample Ljung-Box rejection does not add lags and does not difference the log-growth.

## 3. Stored sample

The contiguous log-growth sample runs from February 1919 to September 2026, 1,292 months. No growth month was left out of that run. The full-sample mean of the log-growth is 0.00236844. The historical mean at the first origin, which uses only the first 120 growth months, is 0.00360595. Forecasts are left in log-growth units.

The augmented Dickey-Fuller statistic is -10.429919, with a used lag of 12 and a five percent critical value of -2.863802. The p-value stored from the check is 0. The check rejects a unit root at five percent. The log-growth was not differenced again.

## 4. In-sample lag

AIC selects lag 12. That is the predeclared maximum, so the ceiling binds. A longer lag was not tried after seeing this result. The same lag, 12, is the modal lag chosen inside the rolling origins. The in-sample AIC is -10573.628498. That fit is not forecast skill.

Ljung-Box at lag 24 has statistic 25.528763 and p-value 0.012507. It rejects uncorrelated residuals at five percent. The lag was not increased to chase that diagnostic.

## 5. Rolling-origin scores

| Horizon | Origins | Autoregression MAE | Autoregression RMSE | Historical-mean MAE | Historical-mean RMSE | Beat the historical mean |
| --- | --- | --- | --- | --- | --- | --- |
| 1 month | 1,172 | 0.00904378 | 0.01588197 | 0.00999415 | 0.01785092 | Yes |
| 12 months | 1,161 | 0.01009907 | 0.01814412 | 0.00999240 | 0.01788324 | No |

The one-month horizon beat the historical mean on both scores. The 12-month horizon did not. The method is not empirically qualified as a forecast.

## 6. Registration

`AutoregressiveBenchmarkMethod` is registered in `default_method_registry`. `refresh.py` is unchanged because this is a full-sample estimate, not an idempotent single-series refresh:

```python
from aqil_research.methods.autoregressive_benchmark import (
    AutoregressiveBenchmarkMethod,
)

registry.register(AutoregressiveBenchmarkMethod())
```

## 7. What this run does not claim

The run is not a product forecast and it is not approved for publication. `publication_allowed` is false. It is not an operational acceptance. Revision sensitivity is blocked because the input is `latest_revised`. `npm run test:research` was not run for this note.
