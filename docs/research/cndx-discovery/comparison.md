# Matched comparison

Anchors require a CNDX month-end and a VWRA month-end within five days, on or after 2019-07-25. The shared date is the earlier session. A state after that date is dropped. The excess is the CNDX session-step return minus the VWRA session-step return. No excess model was selected from two separately fitted absolute models. Matched logistic allowed: False. Non-overlapping keeps: 13.

Relative classification: structural_exposure_or_price_momentum.
Unemployment excess partial survives the price control: False.
Real GDP excess partial survives the price control: False.

The price control is `VWRA:trailing_return_252`. The price-only relative control is `CNDX:relative_performance_vs_vwra_252`. An excess partial survives only when its absolute partial Spearman is strictly greater than the absolute Spearman of that relative control. Otherwise the relative result is structural exposure or price momentum, not macroeconomic information.

## Unemployment and real GDP

### `bls.ln.LNS14000000:year_on_year`

- `CNDX` `conditional_advance` outcome `cndx_return_126` paired `none`: result 0.075, class descriptive, sample 65, non-overlapping 13, refusal none.
- `CNDX` `conditional_decline` outcome `cndx_return_126` paired `none`: result -0.16, class descriptive, sample 65, non-overlapping 13, refusal none.
- `CNDX` `logistic_probit` outcome `cndx_advance_126` paired `none`: result refused, class insufficient_sample, sample 11, non-overlapping 13, refusal not_estimable_effective_sample.
- `CNDX` `pearson` outcome `cndx_return_126` paired `none`: result 0.3567436236447829796928022485, class descriptive, sample 65, non-overlapping 13, refusal none.
- `CNDX` `spearman` outcome `cndx_return_126` paired `none`: result 0.3090635772811806274983338588, class descriptive, sample 65, non-overlapping 13, refusal none.
- `CNDX` `partial_pearson` outcome `cndx_return_126` paired `CNDX:relative_performance_vs_vwra_252`: result 0.3606747666437035261612582739, class descriptive, sample 53, non-overlapping 13, refusal none.
- `CNDX` `partial_spearman` outcome `cndx_return_126` paired `CNDX:relative_performance_vs_vwra_252`: result 0.2573461719656137920326111513, class descriptive, sample 53, non-overlapping 13, refusal none.
- `CNDX` `partial_pearson` outcome `cndx_return_126` paired `VWRA:trailing_return_252`: result 0.3041020837733154166259698807, class descriptive, sample 53, non-overlapping 13, refusal none.
- `CNDX` `partial_spearman` outcome `cndx_return_126` paired `VWRA:trailing_return_252`: result 0.269687525004685442952926526, class descriptive, sample 53, non-overlapping 13, refusal none.
- `CNDX-VWRA` `conditional_cndx_ahead` outcome `excess_126` paired `none`: result -0.11, class descriptive, sample 65, non-overlapping 13, refusal none.
- `CNDX-VWRA` `conditional_vwra_ahead` outcome `excess_126` paired `none`: result 0.11, class descriptive, sample 65, non-overlapping 13, refusal none.
- `CNDX-VWRA` `logistic_probit` outcome `excess_positive_126` paired `none`: result refused, class insufficient_sample, sample 11, non-overlapping 13, refusal not_estimable_effective_sample.
- `CNDX-VWRA` `pearson` outcome `excess_126` paired `none`: result -0.08459186668764793394292531994, class descriptive, sample 65, non-overlapping 13, refusal none.
- `CNDX-VWRA` `spearman` outcome `excess_126` paired `none`: result -0.2002537763489130157366601664, class descriptive, sample 65, non-overlapping 13, refusal none.
- `CNDX-VWRA` `partial_pearson` outcome `excess_126` paired `CNDX:relative_performance_vs_vwra_252`: result 0.1149716247453453244542669637, class descriptive, sample 53, non-overlapping 13, refusal none.
- `CNDX-VWRA` `partial_spearman` outcome `excess_126` paired `CNDX:relative_performance_vs_vwra_252`: result 0.01378011123206880057596038389, class descriptive, sample 53, non-overlapping 13, refusal none.
- `CNDX-VWRA` `pearson_relation` outcome `cndx_minus_vwra` paired `VWRA`: result signs_agree, class descriptive, sample 89, non-overlapping 13, refusal none.
- `CNDX-VWRA` `spearman_relation` outcome `cndx_minus_vwra` paired `VWRA`: result signs_agree, class descriptive, sample 89, non-overlapping 13, refusal none.
- `CNDX-VWRA` `partial_pearson` outcome `excess_126` paired `VWRA:trailing_return_252`: result -0.2093313430881598047733268911, class descriptive, sample 53, non-overlapping 13, refusal none.
- `CNDX-VWRA` `partial_spearman` outcome `excess_126` paired `VWRA:trailing_return_252`: result -0.1603286655929200410418669971, class descriptive, sample 53, non-overlapping 13, refusal none.
- `VWRA` `conditional_advance` outcome `vwra_return_126` paired `none`: result 0.58, class descriptive, sample 65, non-overlapping 13, refusal none.
- `VWRA` `conditional_decline` outcome `vwra_return_126` paired `none`: result -0.16, class descriptive, sample 65, non-overlapping 13, refusal none.
- `VWRA` `logistic_probit` outcome `vwra_advance_126` paired `none`: result refused, class insufficient_sample, sample 11, non-overlapping 13, refusal not_estimable_effective_sample.
- `VWRA` `pearson` outcome `vwra_return_126` paired `none`: result 0.526593649660640689777449218, class descriptive, sample 65, non-overlapping 13, refusal none.
- `VWRA` `spearman` outcome `vwra_return_126` paired `none`: result 0.665850367755166868838672139, class descriptive, sample 65, non-overlapping 13, refusal none.
- `VWRA` `partial_pearson` outcome `vwra_return_126` paired `CNDX:relative_performance_vs_vwra_252`: result 0.4449712627774916578428237119, class descriptive, sample 53, non-overlapping 13, refusal none.
- `VWRA` `partial_spearman` outcome `vwra_return_126` paired `CNDX:relative_performance_vs_vwra_252`: result 0.4905424140929787587327114105, class descriptive, sample 53, non-overlapping 13, refusal none.
- `VWRA` `partial_pearson` outcome `vwra_return_126` paired `VWRA:trailing_return_252`: result 0.5470557473990830224747223368, class descriptive, sample 53, non-overlapping 13, refusal none.
- `VWRA` `partial_spearman` outcome `vwra_return_126` paired `VWRA:trailing_return_252`: result 0.5953905283969676636001181456, class descriptive, sample 53, non-overlapping 13, refusal none.

### `bea.nipa.T10106.A191RX:trailing_standardisation`

- `CNDX` `conditional_advance` outcome `cndx_return_126` paired `none`: result -0.0590717299578059071729957806, class descriptive, sample 82, non-overlapping 13, refusal none.
- `CNDX` `conditional_decline` outcome `cndx_return_126` paired `none`: result 0.08860759493670886075949367089, class descriptive, sample 82, non-overlapping 13, refusal none.
- `CNDX` `logistic_probit` outcome `cndx_advance_126` paired `none`: result refused, class insufficient_sample, sample 13, non-overlapping 13, refusal not_estimable_effective_sample.
- `CNDX` `pearson` outcome `cndx_return_126` paired `none`: result -0.2736823031375844757581755226, class descriptive, sample 82, non-overlapping 13, refusal none.
- `CNDX` `spearman` outcome `cndx_return_126` paired `none`: result -0.4096379743529778870909386777, class descriptive, sample 82, non-overlapping 13, refusal none.
- `CNDX` `partial_pearson` outcome `cndx_return_126` paired `CNDX:relative_performance_vs_vwra_252`: result -0.3289319598752900574942303446, class descriptive, sample 70, non-overlapping 13, refusal none.
- `CNDX` `partial_spearman` outcome `cndx_return_126` paired `CNDX:relative_performance_vs_vwra_252`: result -0.4643431519371662332634861424, class descriptive, sample 70, non-overlapping 13, refusal none.
- `CNDX` `partial_pearson` outcome `cndx_return_126` paired `VWRA:trailing_return_252`: result -0.2904808619120307390576738348, class descriptive, sample 70, non-overlapping 13, refusal none.
- `CNDX` `partial_spearman` outcome `cndx_return_126` paired `VWRA:trailing_return_252`: result -0.4566316587793128428762737882, class descriptive, sample 70, non-overlapping 13, refusal none.
- `CNDX-VWRA` `conditional_cndx_ahead` outcome `excess_126` paired `none`: result 0.00421940928270042194092827, class descriptive, sample 82, non-overlapping 13, refusal none.
- `CNDX-VWRA` `conditional_vwra_ahead` outcome `excess_126` paired `none`: result -0.00421940928270042194092827, class descriptive, sample 82, non-overlapping 13, refusal none.
- `CNDX-VWRA` `logistic_probit` outcome `excess_positive_126` paired `none`: result refused, class insufficient_sample, sample 13, non-overlapping 13, refusal not_estimable_effective_sample.
- `CNDX-VWRA` `pearson` outcome `excess_126` paired `none`: result 0.1113494831621724863053590968, class descriptive, sample 82, non-overlapping 13, refusal none.
- `CNDX-VWRA` `spearman` outcome `excess_126` paired `none`: result -0.02529812613111704457562808849, class descriptive, sample 82, non-overlapping 13, refusal none.
- `CNDX-VWRA` `partial_pearson` outcome `excess_126` paired `CNDX:relative_performance_vs_vwra_252`: result -0.1922758636074435676478195911, class descriptive, sample 70, non-overlapping 13, refusal none.
- `CNDX-VWRA` `partial_spearman` outcome `excess_126` paired `CNDX:relative_performance_vs_vwra_252`: result -0.2771369993296369101969312751, class descriptive, sample 70, non-overlapping 13, refusal none.
- `CNDX-VWRA` `pearson_relation` outcome `cndx_minus_vwra` paired `VWRA`: result signs_agree, class descriptive, sample 89, non-overlapping 13, refusal none.
- `CNDX-VWRA` `spearman_relation` outcome `cndx_minus_vwra` paired `VWRA`: result signs_agree, class descriptive, sample 89, non-overlapping 13, refusal none.
- `CNDX-VWRA` `partial_pearson` outcome `excess_126` paired `VWRA:trailing_return_252`: result 0.03770910474810766296977454816, class descriptive, sample 70, non-overlapping 13, refusal none.
- `CNDX-VWRA` `partial_spearman` outcome `excess_126` paired `VWRA:trailing_return_252`: result -0.1859089334048536164083134521, class descriptive, sample 70, non-overlapping 13, refusal none.
- `VWRA` `conditional_advance` outcome `vwra_return_126` paired `none`: result -0.5696202531645569620253164557, class descriptive, sample 82, non-overlapping 13, refusal none.
- `VWRA` `conditional_decline` outcome `vwra_return_126` paired `none`: result 0.08860759493670886075949367089, class descriptive, sample 82, non-overlapping 13, refusal none.
- `VWRA` `logistic_probit` outcome `vwra_advance_126` paired `none`: result refused, class insufficient_sample, sample 13, non-overlapping 13, refusal not_estimable_effective_sample.
- `VWRA` `pearson` outcome `vwra_return_126` paired `none`: result -0.4765245880821948948114214706, class descriptive, sample 82, non-overlapping 13, refusal none.
- `VWRA` `spearman` outcome `vwra_return_126` paired `none`: result -0.6631310789392936195863734671, class descriptive, sample 82, non-overlapping 13, refusal none.
- `VWRA` `partial_pearson` outcome `vwra_return_126` paired `CNDX:relative_performance_vs_vwra_252`: result -0.3598232859735599254726516596, class descriptive, sample 70, non-overlapping 13, refusal none.
- `VWRA` `partial_spearman` outcome `vwra_return_126` paired `CNDX:relative_performance_vs_vwra_252`: result -0.5471677453357816665230280162, class descriptive, sample 70, non-overlapping 13, refusal none.
- `VWRA` `partial_pearson` outcome `vwra_return_126` paired `VWRA:trailing_return_252`: result -0.4518842084430877048443761814, class descriptive, sample 70, non-overlapping 13, refusal none.
- `VWRA` `partial_spearman` outcome `vwra_return_126` paired `VWRA:trailing_return_252`: result -0.6009969529868817807824839727, class descriptive, sample 70, non-overlapping 13, refusal none.

## Classification row

- `CNDX-VWRA` `predeclared_rule` outcome `excess_126` paired `VWRA:trailing_return_252`: result structural_exposure_or_price_momentum, class descriptive, sample 89, non-overlapping 13, refusal none.
