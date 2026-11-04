# CNDX and VWRA comparison

Retrospective latest-revised research. It is not a point-in-time signal and not a historically executable allocation. The 2019 to 2026 overlap was already inspected by the VWRA and EIMI programmes and is not an untouched holdout. `publication_allowed` stays false. This record is not Verified.

Specification `CNDX-VWRA-COMPARISON-001` version 1. Hash `c46501ee3a41481c5980df8148d327b6c8f4074ce851676c4d7256e795c73249`.
Stored git commit `17a571716f7faf436a2480793585bfa0944a0981`.
Reproduction: `uv run python -m aqil_research.long_horizon.vwra_discovery.cndx`.

CNDX month-end anchors: 121, 2016-11-30 to 2026-11-02.
First stored CNDX session: 2016-11-03. Stored sessions: 2525.
VWRA month-end anchors: 89, 2019-07-31 to 2026-11-02.
First stored VWRA session: 2019-07-25. Stored sessions: 1838.
Matched anchors on or after 2019-07-25: 89, 2019-07-31 to 2026-11-02. Widest day gap: 0.
Executed trials 4227. Refused trials 1814.
Relative classification: structural_exposure_or_price_momentum. A higher terminal wealth is not economically useful or forward-validated.

## Artefacts

- `LH-X-019` `f22ccfee64adc2fcbbbb3a367625cf288c2169069df54a3e4748047595a464d1`
- `LH-X-020` `41e25b20893fa8709ee1d5155e78f22ec439f12d5e53776e031bb6f3c596a534`
- `LH-X-021` `4a8fcfd086da8d2605fb20274c64e6b0009b2ed2806d734300ee6e8ecb41e385`
- `LH-X-022` `d89099d2479d80eb924ae0c73cef43e875c27322569c019179bad9c5f39145dc`
- `LH-X-023` `fed7a40593e6478fe9fc2cb3524b2d1f622055ed6b2369b358b564fa72eab979`
- `LH-X-024` `7dd0b6ab0ac0beae933e8080b6e15e1e4fc48437a4fcc0dbcbb3cc2a19e1f41f`
- `LH-X-025` `a20fb40d53d38156c8f216577eb01b83af40bd80309b41b68629ff981f6e42a3`

## Findings

- `CNDX-F-019` `descriptive`. LH-E-019 stores 23 descriptive or comparison rows and 3 refusals. Overlapping month-ends are not independent replications. Nothing in this row is statistically supported, economically useful, or forward-validated.
- `CNDX-F-020` `descriptive`. LH-E-020 stores 1220 descriptive or comparison rows and 279 refusals. Overlapping month-ends are not independent replications. Nothing in this row is statistically supported, economically useful, or forward-validated.
- `CNDX-F-021` `descriptive`. LH-E-021 stores 24 descriptive or comparison rows and 0 refusals. Overlapping month-ends are not independent replications. Nothing in this row is statistically supported, economically useful, or forward-validated.
- `CNDX-F-022` `retrospective_exploratory`. The CNDX sequence comparison is no_incremental_information, stored as retrospective_exploratory. The stored sign is strictly positive. The 0.05 binary was not substituted. The thresholds were not retuned and the sequence is not an executable strategy.
- `CNDX-F-023` `descriptive`. LH-E-023 stores 2954 descriptive or comparison rows and 1532 refusals. The relative classification is structural_exposure_or_price_momentum. Overlapping month-ends are not independent replications. Nothing in this row is statistically supported, economically useful, or forward-validated.
- `CNDX-F-024` `descriptive`. LH-E-024 casebook counts, which may overlap: CNDX ahead 17, VWRA ahead 1, both advance 33, both decline 5, CNDX up and VWRA down 5, CNDX down and VWRA up 3, leadership reversal 0, approximately neutral 64.
- `CNDX-F-025` `inconclusive`. The price-only comparison is inconclusive. Terminal wealth values are calendar_rebalance 163956.721913171, cash_flow_only 164287.672348133, immediate_cndx 178318.51337504, immediate_vwra 150430.016335996, relative_momentum 158175.154836101, static_mix 163548.411567951, threshold_rebalance 164287.672348133. These are split-adjusted US-dollar price paths with the category C cost rate. They are not total returns, not SGD investor returns, not economically useful, and not forward-validated. Bounded VWRA-to-CNDX rotation is blocked and was not implemented. No stored policy sells one listing to buy the other under a bound.

## Portfolio

The price-only comparison is inconclusive. Terminal wealth values are calendar_rebalance 163956.721913171, cash_flow_only 164287.672348133, immediate_cndx 178318.51337504, immediate_vwra 150430.016335996, relative_momentum 158175.154836101, static_mix 163548.411567951, threshold_rebalance 164287.672348133. These are split-adjusted US-dollar price paths with the category C cost rate. They are not total returns, not SGD investor returns, not economically useful, and not forward-validated. Bounded VWRA-to-CNDX rotation is blocked and was not implemented. No stored policy sells one listing to buy the other under a bound.

The prices are split-adjusted closes. They are not distribution-adjusted total returns. See `return-audit.md`.
