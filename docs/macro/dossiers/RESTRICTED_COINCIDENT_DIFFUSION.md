# Restricted coincident diffusion

**Status:** implemented on the same balanced panel as the Stock–Watson modern refit. Not the Chicago Fed national activity index. Not publication eligible.
**Method:** `RESTRICTED_COINCIDENT_DIFFUSION`, version `0.1.0`.
**Publication:** `publication_allowed` is false.

## Identity

This is a breadth measure on four procyclical levels. It is not the Chicago Fed 85-indicator index. It is not a principal-component factor and it is not the Stock–Watson coincident factor.

The panel is the balanced latest-revised months from January 1997 of:

- `fed.g17.IP.B50001.S`
- `bea.nipa.T20600.W875RX`
- `bea.nipa.U002BU.KPMT`
- `bls.ce.CES0000000001`

That is the same panel as `STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT`. Payroll headcount is not employee-hours. 2017 chained dollars are not 1982 dollars. This is not the CITIBASE 1959–87 payroll specification.

## Definition

Each series enters as a three-month arithmetic change in the level: the current month minus the month three calendar months earlier. An increase is an improvement for every series. A zero change is not an improvement. There is no interpolation. If either endpoint is missing, that series is omitted from the month's denominator. The denominator is the number of series actually observed at both endpoints.

The share is the number of improving series divided by that denominator. A month with denominator zero has no share.

Persistence is the number of consecutive months, ending at the current month, for which the share is at or above one half. A share below one half, or a month with denominator zero, resets the count to zero. A share of exactly one half continues the count.

The path is `latest_revised`. It is not a real-time vintage.

## Correlation with the filtered factor

The diffusion share is correlated with the Stock–Watson filtered factor on the months where both exist. That correlation is not independent confirmation. Both calculations use the same four series. The filtered factor is not the smoother.

## Registration

The estimator is not in `registry.py`. The integrator adds this call inside `default_method_registry`:

```python
from aqil_research.methods.restricted_coincident_diffusion import (
    RestrictedCoincidentDiffusionMethod,
)

registry.register(RestrictedCoincidentDiffusionMethod())
```

## Acceptance

The method is implemented. It is not operationally accepted. `publication_allowed` stays false.

## Stored run, 30 October 2026

Run 1f747c9f-4851-4588-a4dc-d8fb1ff30558. publication_allowed is false. The balanced level sample has 355 months, from January 1997 to July 2026. January, February, and March 1997 have denominator zero because the three-month lag is outside that extract and was not interpolated. The other 352 months have denominator 4. No series was dropped inside those months.

The Pearson correlation of the diffusion share with the Stock–Watson filtered factor is 0.3362474222888005 on 352 overlapping months. The factor is the preserved run 3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a, which is still the adopted parameter version. The correlation is not independent confirmation.

The longest persistence count in this sample is 58 months. July 2026 has share 1 and persistence 8.

