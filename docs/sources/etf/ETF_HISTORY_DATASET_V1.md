# Historical research dataset v1

Status: register frozen. Split-adjusted daily bars for 19 listings are stored on the local ETF database. INRG remains unstored. Owner: ETF workstream. Decision date: 3 November 2026.

The founder ratified `ETF_UNIVERSE_V1_2026-11-03` in `docs/sources/etf/register/`. That artifact is the research universe. It is not a trade instruction. Eighteen equity share classes are approved for research. INRG is conditional and distributing. EUNA, ISIN IE00BDBRDM35, is a research comparator and is not an equity approval.

The research window is 3 November 2016 to 2 November 2026, daily completed sessions. History starts at the genuine available date. No pre-inception price is created.

On 3 November 2026 the TradingView Data API returned split-adjusted Japanese daily candles. Those closes are stored as `adjusted_close` on `aqil_etf.instruments.market_price_observations`. The stored observation count is 42931. INRG is zero: its London row is GBX, not USD, and it was not rescaled. The 2 November 2026 candle was kept. It was a completed London close when it was retrieved, not an open session. A second insert did not add rows.

The dividends sample for VWRA stays a separate cached series. It is not stored as a total-return index. Saxo bars were not copied. The preserved database `postgres` was not reset and does not hold these prices. No hosted migration was applied.

This list was selected in 2026. Funds that closed before selection are absent. A backtest of these twenty instruments is not an unbiased historical ETF selection strategy.

Dataset identity: `aqil-etf-history-v1-2026-11`.