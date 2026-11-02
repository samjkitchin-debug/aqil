# Historical research dataset v1

Status: register frozen. Split-adjusted daily bars for 19 listings are stored on the local ETF database. INRG remains unstored. Owner: ETF workstream. Decision date: 3 November 2026.

The founder ratified `ETF_UNIVERSE_V1_2026-11-03` in `docs/sources/etf/register/`. That artifact is the research universe. It is not a trade instruction. Eighteen equity share classes are approved for research. INRG is conditional and distributing. EUNA, ISIN IE00BDBRDM35, is a research comparator and is not an equity approval.

The research window is 3 November 2016 to 2 November 2026, daily completed sessions. History starts at the genuine available date. No pre-inception price is created.

On 3 November 2026 the TradingView Data API returned split-adjusted Japanese daily candles. Those closes are stored as `adjusted_close` on `aqil_etf.instruments.market_price_observations`. The stored observation count is 42931. INRG is zero: its London row is GBX, not USD, and it was not rescaled. The 2 November 2026 candle was kept. It was a completed London close when it was retrieved, not an open session. A second insert did not add rows.

The dividends sample for VWRA stays a separate cached series. It is not stored as a total-return index. Saxo bars were not copied. The preserved database `postgres` was not reset and does not hold these prices. No hosted migration was applied.

This list was selected in 2026. Funds that closed before selection are absent. A backtest of these twenty instruments is not an unbiased historical ETF selection strategy.

Dataset identity: `aqil-etf-history-v1-2026-11`.

Preservation on 3 November 2026 copied this local database to `C:\Users\gamer\aqil-release-backups\2026-11-03-etf-history\aqil_etf.dump` (1629423 bytes, SHA-256 `B7598DC08AEE375B4E29F66A0423075EAED2A6527B0DDBCBE1F1FE3C6BB96BEB`). A restore into disposable database `aqil_etf_restore_20261103` matched 42931 observations and 1838 VWRA rows, and that disposable database was dropped. The hosted project does not hold this history. No FX series and no total-return index were added. RBOT, 2524 rows from 2016-11-03 to 2026-11-02, has no session on 2025-12-19. The other eighteen stored symbols have that session. TradingView Data API is a third-party API, not TradingView Inc. Forty-one calls were used and nineteen remain in the 60-call cap. Access stays founder-only. Saxo bars stay preserved and were not copied. Browser acceptance and a production deploy were not done. The survivorship limit above still applies. The merge to `main` was not made: the rights-fragment tests still expect every ETF fragment to refuse automated collection, and `tradingview_data_api.csv` records that collection as permitted. The single next task is P1 resolve the INRG listing currency.
