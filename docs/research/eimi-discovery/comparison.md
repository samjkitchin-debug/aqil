# Matched comparison

Both listings are US-dollar London lines. The outcome is the EIMI session-step return minus the VWRA session-step return. A missing session is censored. Relative outperformance is not a positive absolute return. Matched anchors: 89. Non-overlapping 126-session keeps: 13. Logistic floors met on the excess: False.

## Exclusive classes

The five classes are exclusive at zero. Censored rows are counted separately.

| Outcome | Class | Count | Sample |
| --- | --- | ---: | ---: |
| excess_126 | both_negative_eimi_declines_less | 1 | 82 |
| excess_126 | censored | 7 | 89 |
| excess_126 | eimi_ahead_both_positive | 26 | 82 |
| excess_126 | eimi_positive_vwra_negative | 2 | 82 |
| excess_126 | no_sign | 0 | 82 |
| excess_126 | vwra_ahead | 53 | 82 |
| excess_21 | both_negative_eimi_declines_less | 12 | 87 |
| excess_21 | censored | 2 | 89 |
| excess_21 | eimi_ahead_both_positive | 25 | 87 |
| excess_21 | eimi_positive_vwra_negative | 3 | 87 |
| excess_21 | no_sign | 0 | 87 |
| excess_21 | vwra_ahead | 47 | 87 |
| excess_252 | both_negative_eimi_declines_less | 0 | 76 |
| excess_252 | censored | 13 | 89 |
| excess_252 | eimi_ahead_both_positive | 24 | 76 |
| excess_252 | eimi_positive_vwra_negative | 0 | 76 |
| excess_252 | no_sign | 0 | 76 |
| excess_252 | vwra_ahead | 52 | 76 |
| excess_504 | both_negative_eimi_declines_less | 0 | 64 |
| excess_504 | censored | 25 | 89 |
| excess_504 | eimi_ahead_both_positive | 10 | 64 |
| excess_504 | eimi_positive_vwra_negative | 0 | 64 |
| excess_504 | no_sign | 0 | 64 |
| excess_504 | vwra_ahead | 54 | 64 |
| excess_63 | both_negative_eimi_declines_less | 4 | 85 |
| excess_63 | censored | 4 | 89 |
| excess_63 | eimi_ahead_both_positive | 32 | 85 |
| excess_63 | eimi_positive_vwra_negative | 3 | 85 |
| excess_63 | no_sign | 0 | 85 |
| excess_63 | vwra_ahead | 46 | 85 |
| excess_756 | both_negative_eimi_declines_less | 0 | 52 |
| excess_756 | censored | 37 | 89 |
| excess_756 | eimi_ahead_both_positive | 6 | 52 |
| excess_756 | eimi_positive_vwra_negative | 0 | 52 |
| excess_756 | no_sign | 0 | 52 |
| excess_756 | vwra_ahead | 46 | 52 |

## Unemployment and real GDP

The original feature definitions are scored again on the matched sample. Signs differ only when both Spearman coefficients are strictly opposite.

### `bls.ln.LNS14000000:year_on_year`

- EIMI spearman eimi_return_126: 0.6352305242767398022122715019 (n=65)
- EIMI-VWRA spearman excess_126: 0.2860549520388197174333528086 (n=65)
- VWRA spearman vwra_return_126: 0.665850367755166868838672139 (n=65)
- EIMI pearson eimi_return_126: 0.5719987639861453451863158905 (n=65)
- EIMI-VWRA pearson excess_126: 0.34767332003835783723371698 (n=65)
- VWRA pearson vwra_return_126: 0.526593649660640689777449218 (n=65)
- EIMI partial_pearson eimi_return_126: 0.4652960262238718199491726825 (n=53), control `EIMI:relative_performance_vs_vwra_252`
- EIMI partial_pearson eimi_return_126: 0.4823334999201884463639633825 (n=53), control `VWRA:trailing_return_252`
- EIMI-VWRA partial_pearson excess_126: 0.2204445244442530171216360331 (n=53), control `EIMI:relative_performance_vs_vwra_252`
- EIMI-VWRA partial_pearson excess_126: 0.1164013845094278801589651506 (n=53), control `VWRA:trailing_return_252`
- VWRA partial_pearson vwra_return_126: 0.489201593114466974921486807 (n=53), control `EIMI:relative_performance_vs_vwra_252`
- VWRA partial_pearson vwra_return_126: 0.5470557473990830224747223368 (n=53), control `VWRA:trailing_return_252`
- EIMI partial_spearman eimi_return_126: 0.4870344166633381280458420175 (n=53), control `EIMI:relative_performance_vs_vwra_252`
- EIMI partial_spearman eimi_return_126: 0.5278952286863891109550246352 (n=53), control `VWRA:trailing_return_252`
- EIMI-VWRA partial_spearman excess_126: 0.2042854847035780813547022903 (n=53), control `EIMI:relative_performance_vs_vwra_252`
- EIMI-VWRA partial_spearman excess_126: 0.1522633701779133724987994277 (n=53), control `VWRA:trailing_return_252`
- VWRA partial_spearman vwra_return_126: 0.5368210703066744061719353489 (n=53), control `EIMI:relative_performance_vs_vwra_252`
- VWRA partial_spearman vwra_return_126: 0.5953905283969676636001181456 (n=53), control `VWRA:trailing_return_252`
- pearson_relation: signs_agree.
- spearman_relation: signs_agree.

### `bea.nipa.T10106.A191RX:trailing_standardisation`

- EIMI spearman eimi_return_126: -0.5936075157791338208042771619 (n=82)
- EIMI-VWRA spearman excess_126: -0.1696052588747382058634661429 (n=82)
- VWRA spearman vwra_return_126: -0.6631310789392936195863734671 (n=82)
- EIMI pearson eimi_return_126: -0.5000849127511031270194891935 (n=82)
- EIMI-VWRA pearson excess_126: -0.2814745393551622623603191214 (n=82)
- VWRA pearson vwra_return_126: -0.4765245880821948948114214706 (n=82)
- EIMI partial_pearson eimi_return_126: -0.4264028645107206455633200414 (n=70), control `EIMI:relative_performance_vs_vwra_252`
- EIMI partial_pearson eimi_return_126: -0.4739385822260980206097287543 (n=70), control `VWRA:trailing_return_252`
- EIMI-VWRA partial_pearson excess_126: -0.2589222816906602461819397135 (n=70), control `EIMI:relative_performance_vs_vwra_252`
- EIMI-VWRA partial_pearson excess_126: -0.2457007069945486748388998108 (n=70), control `VWRA:trailing_return_252`
- VWRA partial_pearson vwra_return_126: -0.3926142670509419300109969988 (n=70), control `EIMI:relative_performance_vs_vwra_252`
- VWRA partial_pearson vwra_return_126: -0.4518842084430877048443761814 (n=70), control `VWRA:trailing_return_252`
- EIMI partial_spearman eimi_return_126: -0.4081232577666068634595797375 (n=70), control `EIMI:relative_performance_vs_vwra_252`
- EIMI partial_spearman eimi_return_126: -0.5138975533225763708098579757 (n=70), control `VWRA:trailing_return_252`
- EIMI-VWRA partial_spearman excess_126: -0.1052672426098494037854798194 (n=70), control `EIMI:relative_performance_vs_vwra_252`
- EIMI-VWRA partial_spearman excess_126: -0.09185570776368814440951522187 (n=70), control `VWRA:trailing_return_252`
- VWRA partial_spearman vwra_return_126: -0.4773377375054285629604093011 (n=70), control `EIMI:relative_performance_vs_vwra_252`
- VWRA partial_spearman vwra_return_126: -0.6009969529868817807824839727 (n=70), control `VWRA:trailing_return_252`
- pearson_relation: signs_agree.
- spearman_relation: signs_agree.

## Excess against the eight pairs and price-only momentum

- `SEQ-INF-MOM-001` / `none` conjunction_comparison: no_incremental_information.
- `EIMI:relative_performance_vs_vwra_252` / `eight_pairs` control_increment: inconclusive.
- `SEQ-INF-MOM-001` / `none` conjunction_comparison: no_incremental_information.
- `bis.ws_gli.Q.USD.3P.N.A.I.B.USD:percent_change` / `fed.g17.IP.B50001.S:year_on_year` conjunction_comparison: inconclusive.
- `bls.cu.CUSR0000SA0:year_on_year` / `drawdown_252` conjunction_comparison: no_incremental_information.
- `fed.g17.IP.B50001.S:year_on_year` / `bls.cu.CUSR0000SA0:year_on_year` conjunction_comparison: inconclusive.
- `fed.g17.IP.B50001.S:year_on_year` / `fed.sloos.SUBLPDCILS_N.Q:level` conjunction_comparison: inconclusive.
- `fed.g17.IP.B50001.S:year_on_year` / `trailing_return_63` conjunction_comparison: inconclusive.
- `fed.h15.RIFSPFF_N.M:difference` / `method:ESTRELLA_MISHKIN_TERM_SPREAD:spread` conjunction_comparison: no_incremental_information.
- `fed.sloos.SUBLPDCILS_N.Q:level` / `fed.h15.RIFSPFF_N.M:difference` conjunction_comparison: no_incremental_information.
- `fx_observations` / `none` currency_intersection: blocked_no_foreign_exchange.
- `method:LABOUR_MARKET_CONDITIONS:unemployment_change_percentage_points` / `bls.cu.CUSR0000SA0:year_on_year` conjunction_comparison: rejected.
- `SEQ-INF-MOM-001` / `none` conjunction_comparison: no_incremental_information.
