# EIMI dossier

The battery is the stored VWRA battery with the symbol set to EIMI. Thresholds were not retuned. A later 126-session return is the outcome, not a state.

Anchors: 121. Non-overlapping 126-session keeps: 18. Logistic and probit floors met: True.

Observed and censored outcomes:

| Steps | Observed | Censored |
| ---: | ---: | ---: |
| 21 | 119 | 2 |
| 63 | 117 | 4 |
| 126 | 114 | 7 |
| 252 | 108 | 13 |
| 504 | 96 | 25 |
| 756 | 84 | 37 |

Sequence comparison: `no_incremental_information`, stored as `retrospective_exploratory`.

- `SEQ-INF-MOM-001` / `none`: no_incremental_information (n=114, class `retrospective_exploratory`).

## Pairs

- `bis.ws_gli.Q.USD.3P.N.A.I.B.USD:percent_change` / `fed.g17.IP.B50001.S:year_on_year`: 0.1272319932539959080844892734 (n=114, class `descriptive`).
- `bls.cu.CUSR0000SA0:year_on_year` / `drawdown_252`: -0.2831244504954506262019166544 (n=97, class `descriptive`).
- `fed.g17.IP.B50001.S:year_on_year` / `bls.cu.CUSR0000SA0:year_on_year`: 0.4562704339816381457512238822 (n=109, class `descriptive`).
- `fed.g17.IP.B50001.S:year_on_year` / `fed.sloos.SUBLPDCILS_N.Q:level`: -0.6088081243749284412909848659 (n=114, class `descriptive`).
- `fed.g17.IP.B50001.S:year_on_year` / `trailing_return_63`: -0.2502544937366300338053283364 (n=111, class `descriptive`).
- `fed.h15.RIFSPFF_N.M:difference` / `method:ESTRELLA_MISHKIN_TERM_SPREAD:spread`: 0.1472285496616191114736220276 (n=114, class `descriptive`).
- `fed.sloos.SUBLPDCILS_N.Q:level` / `fed.h15.RIFSPFF_N.M:difference`: -0.03275348756619703633795978981 (n=114, class `descriptive`).
- `method:LABOUR_MARKET_CONDITIONS:unemployment_change_percentage_points` / `bls.cu.CUSR0000SA0:year_on_year`: -0.4760571899267758610719079335 (n=109, class `descriptive`).

Benjamini–Hochberg flag count on the EIMI Spearman rows: 83. The flag cannot promote a claim.
