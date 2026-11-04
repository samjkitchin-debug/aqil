# EIMI and VWRA comparison

Retrospective latest-revised research. It is not a point-in-time signal and not a historically executable allocation. `publication_allowed` stays false. This record is not Verified.

Specification `EIMI-VWRA-COMPARISON-001` version 1. Hash `d59b453d69ffd52b5eeaac8e611fe653d5fd858addb9182f485f6f9415571e37`.
Stored git commit `04af4fb1e1f3630c6c2efbaab040108bd4d1a6b1`.
Reproduction: `uv run python -m aqil_research.long_horizon.vwra_discovery.compare`.

EIMI month-end anchors: 121, 2016-11-30 to 2026-11-02.
First stored EIMI session: 2016-11-03. Stored sessions: 2525.
Matched anchors on or after 2019-07-25: 89, 2019-07-31 to 2026-11-02.
Executed trials 4266. Refused trials 1822.

## Artefacts

- `LH-X-012` `a75948be5b97dc93e356486534a3558ef145b3747bacb2c9ffb37534e279f59d`
- `LH-X-013` `1e5aab16d43940e19b864f1a0ab99774aaffd9e29087a108e974a27a72bc55cf`
- `LH-X-014` `4e6032579bf55a94555127dd7ada106e0c12c6dc02bf228649a921da4748ab56`
- `LH-X-015` `cb10dc34c7c90b4ce192adc849d33210e0a8184335af7a4f8e2294e7ff20cc56`
- `LH-X-016` `0c3a8995ac92c4f51d42c2fca5bf75e379f6ed16bb844a1a299ebaff685f4fc5`
- `LH-X-017` `d66f439c6ab356a44097969d194aa8b40110b1a241ac4d9560a90ca0359779fc`
- `LH-X-018` `cb323cbed16de7873ea000ab564ea84c8ef64090b6270a3823fa75e5038ca220`

## Findings

- `CMP-F-012` `descriptive`. LH-E-012 stores 23 descriptive or comparison rows and 3 refusals. Overlapping month-ends are not independent replications. Nothing in this row is statistically supported, economically useful, or forward-validated.
- `CMP-F-013` `descriptive`. LH-E-013 stores 1228 descriptive or comparison rows and 271 refusals. Overlapping month-ends are not independent replications. Nothing in this row is statistically supported, economically useful, or forward-validated.
- `CMP-F-014` `descriptive`. LH-E-014 stores 24 descriptive or comparison rows and 0 refusals. Overlapping month-ends are not independent replications. Nothing in this row is statistically supported, economically useful, or forward-validated.
- `CMP-F-015` `retrospective_exploratory`. The EIMI sequence comparison is no_incremental_information, stored as retrospective_exploratory. The thresholds were not retuned and the sequence is not an executable strategy.
- `CMP-F-016` `descriptive`. LH-E-016 stores 2985 descriptive or comparison rows and 1548 refusals. Overlapping month-ends are not independent replications. Nothing in this row is statistically supported, economically useful, or forward-validated.
- `CMP-F-017` `insufficient_sample`. LH-E-017 casebook counts, which may overlap: EIMI ahead 5, VWRA ahead 4, both advance 25, both decline 7, leadership reversal 0, approximately neutral 73.
- `CMP-F-018` `rejected`. The price-only comparison is rejected. Terminal wealth values are immediate_eimi 134754.294595556, immediate_vwra 150430.016335996, relative_momentum 145357.70234994, static_mix 142633.337854735. These are split-adjusted US-dollar price paths with the category C cost rate. They are not total returns, not SGD investor returns, not economically useful, and not forward-validated.

The portfolio result is `rejected` on a provisional price-return path.
