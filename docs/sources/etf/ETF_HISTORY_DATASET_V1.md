# Historical research dataset v1

Status: register frozen. Validated daily bars are cached for founder-only research. The database observation count is still zero, so the frozen dataset is not complete. Owner: ETF workstream. Decision date: 3 November 2026.

The founder ratified `ETF_UNIVERSE_V1_2026-11-03` in `docs/sources/etf/register/`. That artifact is the research universe. It is not a trade instruction. Eighteen equity share classes are approved for research. INRG is conditional and distributing. EUNA, ISIN IE00BDBRDM35, is a research comparator and is not an equity approval.

The research window is 3 November 2016 to 2 November 2026, daily completed sessions. History starts at the genuine available date. No pre-inception price is created.

On 3 November 2026 the TradingView Data API returned split-adjusted Japanese daily candles for 19 of the 20 listings. The closes are cached under `workers/research/.local/tradingview/`, which Git ignores. They were not inserted. Local Postgres on port 55432 did not accept a connection, `postgres` was not reset, and no hosted migration was applied. `stored_price_observations` stays 0.

INRG has no London USD row in the search result. The London row is GBX and was not rescaled. Its total return stays insufficient until a distribution series exists. The dividends sample for VWRA is a separate series. Ten overlapping closes matched the splits series and none differed. That sample is not a total-return index.

Saxo live retrieval remains verified and is refused for permanent storage while retention rights are unresolved. No Saxo bar was copied into the cache or the database. A bar-level comparison was not possible because no Saxo price file was available.

This list was selected in 2026. Funds that closed before selection are absent. A backtest of these twenty instruments is not an unbiased historical ETF selection strategy.

Dataset identity reserved for the first licensed import: `aqil-etf-history-v1-2026-11`. Until rows are stored, the observation count is zero.