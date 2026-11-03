# EIMI relative to VWRA

Dossier `LH-X-007`, hypothesis `LH-H-007`.
Status `inconclusive`. Registry result `no_policy_registered`.

Matched US-dollar month-ends within five days. The outcome is the session-step return of EIMI minus the session-step return of VWRA. A missing session is censored and is not filled. Predictors are EIMI's stored state on the matched date, plus the stored relative performance versus VWRA. The primary price-only control is `relative_performance_vs_vwra_252`. Its stored 6-month excess Spearman is `-0.02192284139620330679730557257`. Eighty of the 87 other estimated primary-horizon excess Spearman rows have a larger absolute coefficient. The frozen rule therefore returns `inconclusive`. That status cannot promote a claim. EIMI is an emerging-market overweight relative to VWRA, not a separate diversifier. Relative outperformance is not a positive absolute return. The conjunction is not a trial on this dossier. No allocation policy is registered.

## Counts

- Trials: 1169
- Refused trials: 115
- Trials with an effect: 1054
- Primary-horizon Spearman tests in the diagnostic: 176
- Diagnostic flags: 13
- Eligible conjunction month-ends: not a pair trial

## Primary-horizon classes

- both_negative_eimi_declines_less: 1
- censored: 7
- eimi_ahead_both_positive: 26
- eimi_positive_vwra_negative: 2
- vwra_ahead: 53

The Benjamini-Hochberg flags do not change the status.
Logistic, probit, and regularized searches are refusal rows.
Method rows have no effect. Publication stays false.
