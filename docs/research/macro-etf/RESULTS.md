# Macro-to-ETF results

These figures were computed from the frozen catalogue and the local databases. They are retrospective. They are not point-in-time, not a forecast, and not an allocation.

7 training-window cells meet the statistical rule. They use the 12-month CPI-U change, the 12-month industrial-production change, the 12-month unemployment change, the unemployment level on EIMI at the 1-month and 3-month horizons. They are not independent findings. The features overlap, the horizons overlap, and they share one listing. None of the predeclared cash rules beat immediate investment on the holdout. The economically useful class is empty. The forward-validated class is empty.

## Pilot

The preregistered cell is the 12-month change in unemployment, with an assumed one-month lag, against the 12-month VWRA listing-currency price return. Pearson r is 0.6976183057660493. Spearman r is 0.6036422349612018. The Newey–West slope is 0.03587019471662332 with p 1.7529922183214573e-07. Decision points are 73 and non-overlapping windows are 7. It is below the exploratory floor, so the figures are not an exploratory finding.

## What ran

Gate 1 described 120 full-sample cells that met the exploratory floor. The inferential family held 44 training-window cells. Gate 2 recorded 45 rows, of which 12 are blocked. Gate 3 recorded 72 rows, of which 41 are blocked. Gate 4 stopped: fewer than two Gate 3 outputs carried distinct information. Gate 5 ran on 7 cells. None beat immediate investment on the holdout under both cost assumptions. Gate 6 ran the holdout once.

## Evidence classes

| Evidence class | Rows |
| --- | --- |
| not_claimed | 63 |
| exploratory | 221 |
| statistically_supported | 7 |
| economically_useful | 0 |
| forward_validated | 0 |

## Audit

The inputs are latest-revised series with an assumed one-month lag, so a cell cannot be point-in-time. The ETF list was selected in 2026, and several equity listings share the same retrieved start, so agreement among them is one piece of evidence about a survivor set. Overlapping monthly returns are not treated as independent: the non-overlapping count and the block-bootstrap interval are part of the record. A bootstrap interval that contains zero withdraws a claim to inconclusive. The price ratio is a split-adjusted listing close, not an issuer total-return index and not NAV. No foreign-exchange series was used. EUNA stays in euros. Costs of zero and 10 basis points were assumptions and were applied to the cells that reached Gate 5. Gate 3 did not store a block bootstrap of the added coefficient. No incremental test both met the training statistical floor and survived Benjamini-Hochberg, so Gate 4 had nothing to combine. Nothing in this run was frozen before the outcome, so the forward-validated class is empty. The input hash is `356491cf0dda285a899df98c1ff19d72b19c433ef915d87c5538f767fb7dfbb9`.

Live latest-revised observations were 38653. Adjusted closes were 42931. `publication_allowed` true-count was 0.
