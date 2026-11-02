# ETF read contract V1

**Status:** contract for stored rows. It is not a licence and it does not cite an ISIN.  
**Owner:** founder  
**Date:** 2 November 2026

The web app reads this shape from `instruments` through the server-only `ETF_DATABASE_URL`. It does not import a Saxo client or an issuer adapter. The research reader that assembles the same answers is `aqil_research.etf.read.contract`.

Missing stays missing. A missing price is not zero. A missing approval is not eligibility.

## What a reader may return

| Question | Source | When it is absent |
| --- | --- | --- |
| Identity | `instruments.share_classes` and `instruments.listings` | No ISIN is invented. A ticker is not a share class. `VWRA` on `XLON` and `VWCE` on `XETR` are the same share class only after one cited ISIN ties them. |
| Canadian `CNDX` | Not stored against the London ticker | `CNDX` on `XTSE` or `NEOE` is a different fund and must not be attached. |
| Eligibility | `instruments.eligibility_decisions`, and the existing `instruments.assessments` row | `eligible`, `insufficient`, or `rejected` are conditions. `CORE` is not founder approval and is not a score. |
| Approval | `instruments.approval_decisions` | Append-only. This programme inserts none. An approval needs an actor and a rationale. |
| Latest close | `instruments.market_price_observations` where `price_type` is `close` and `adjustment_status` is `raw` | No licensed close is stored. |
| Adjusted close | A different row, `price_type` `adjusted_close` | It is never written over the raw close. |
| NAV | `instruments.nav_observations` | NAV is not the listing close. |
| Bid, ask, last | Separate market-price rows | A quote is not the close. Delay class stays on the row. |
| Quote unit | `quote_unit` | `GBX` stays `GBX`. It is not divided into `GBP` in the raw row. |
| FX lineage | `instruments.fx_observations` and `instruments.converted_amounts` | No rights-cleared SGD reference rate is stored. Broker FX is a different `rate_semantics`. |
| Holdings | `instruments.holdings_snapshots` with `rights_gate` `permitted` | Prohibited and unknown sources are not fetched. Top-ten completeness stays `partial`. |
| Overlap | Names present in two stored full snapshots | A partial or missing holding list is not an empty portfolio and does not produce a count. |
| Performance | Research-worker calculations, or stored `instruments.fund_returns` | Market, NAV, and total return stay separate. No return before inception. No total return from price changes alone for a distributing class. An accumulating class does not add a dividend on top of an adjusted close. Benchmark series have no `share_class_id`. |
| Refresh | `instruments.etf_refresh_runs` | A failed provider keeps the previous close and its timestamp. A holdings failure does not delete prices. Market closure is not an error. |

## Who may read

`instruments` stays off the Supabase Data API. `anon`, `authenticated`, and `service_role` stay revoked. `research_writer` inserts. `etf_reader` selects and is `NOLOGIN` in Git. The web uses `ETF_DATABASE_URL` for that reader. The password is not in Git.

Production today lets any signed-in Google account open the app. A price row is readable there only when the source rights permit retention and display for that audience. Until then the page says the close is absent.

## Price licence, still required

No vendor is the primary price source. The slot stays `unresolved` after a LIVE retest recorded in `docs/sources/etf/SAXO_MARKET_DATA_PROOF_2026-11-02.md`. `MarketDataViaOpenApiTermsAccepted` was true. London VWRA, EIMI, CNDX, IUIT, and IWMO returned delayed OldIndicative bid and ask, with no last, and 1,200 daily chart closes from 2022-02-01 to 2026-11-02. No HTTP 403 occurred. The rows were not stored. Accepting terms is not permission to display prices to other users. The adapter stays replaceable. Gate E and Gate F are not passed.

The 2 November 2026 price-provider probe retrieved no London or Xetra bar. That note is evidence of those calls. It is not a vendor choice.

Rights rows `eodhd_global_etf_eod`, `twelve_data_global_etf_eod`, `mas_sgd_reference_fx`, and `saxo_sim_infoprices` are disabled and unknown. They are not permission. `vanguard_uk_vwra_holdings` and `ishares_ucits_holdings` stay prohibited.

The terms flag is now true. That consent does not allow these prices to be shown to every signed-in Google account. Before any price is stored, the founder must decide that private research storage in instruments is permitted for the people who can open Explore, or keep the rows unread by anyone else. A later licensed vendor can still take the slot. Close, NAV, bid, ask, last, and adjusted close stay distinct. Gate E and Gate F stay open. Gate O is blocked because nothing was stored and production was not deployed.

## Personal research and EODHD, 2 November 2026

Aqil is a private founder-only research application today. Market-data rules are not designed around commercial redistribution to a large audience. A later commercial licence can still replace the adapter.

`docs/sources/etf/PRICE_VENDOR_FALLBACK_2026-11-02.md` is a fallback note. It does not approve a purchase. Its statement that Saxo requires express written permission before copying or downloading is stronger than the pages retrieved for the Saxo terms section above. Those pages list copying and downloading as misuse and require a separate Saxo agreement before display to other users. They do not close a separate written-permission question. OpenAPI access remains not unrestricted storage.

EODHD personal terms were read at [Terms and conditions](https://eodhd.com/financial-apis/terms-conditions). A Non-Professional User is an individual who views or uses the information solely for their own personal investment activities. The same section says Non-Professional Users are permitted to store, manipulate, and analyse the data for private, non-commercial purposes, and are prohibited from displaying or granting access to the information, in original or repackaged form. The page does not expressly permit showing the series inside an application, even to the account holder alone. The US$19.99 a month EOD Historical All-World plan on [https://eodhd.com/pricing](https://eodhd.com/pricing) names worldwide end-of-day history. It is not recommended for purchase. No registered free key has returned a London bar. The public demo token is not that test.

No `EODHD_API_TOKEN` was present in the process environment or in the gitignored env files that were checked. The founder step, with no payment, is to open [https://eodhd.com/pricing](https://eodhd.com/pricing), choose Start free, complete EODHD's own account form, and place the issued key only in a gitignored server environment as `EODHD_API_TOKEN`.

Licensed ETF prices are read only when `app_metadata.aqil_research` is `founder`, the same claim as unpublished research in ADR 028. Ordinary Google sign-in is not enough. The server does not send a provider key to the browser.

## Saxo market-data terms, read 2 November 2026

Accepting OpenAPI access is not storage consent and not redistribution consent. The pages below were read on 2 November 2026. A permission that is not written on those pages is not claimed.

Personal use of the API by a direct retail client is described in [Can I use OpenAPI for personal use?](https://openapi.help.saxo/hc/en-us/articles/4416505486481-Can-I-use-OpenAPI-for-personal-use), updated 15 October 2026. The retrieved text allows a personal portfolio tool, export of balances and positions, a personal view of market rates and account performance, and a personal trading interface. It does not grant multi-user display.

Private persistent storage and derived research are described in [Can I store and use OpenAPI market data for my own algo or AI/backtesting?](https://openapi.help.saxo/hc/en-us/articles/39663625431581-Can-I-store-and-use-OpenAPI-market-data-for-my-own-algo-or-AI-backtesting), updated 5 October 2026. The retrieved text says the client may store OpenAPI market data for private purposes, including backtesting, strategy validation, and the client's own AI or algo development, with no fixed retention limit, provided the data are not redistributed. The example is a private store of Level 1 quotes from `trade/v1/prices`. It does not name Explore or a database shared with other signed-in users.

Redistribution is prohibited by that same article. Displaying the data to other end users through a product or application requires a separate market-data agreement. A retail market-data subscription covers delivery to the client and private storage. It does not cover delivery to other users or professional or non-personal use. The party that must grant that agreement is Saxo Bank.

[Enabling Market Data](https://developer.saxobank.com/excel/user-guide/enabling-market-data) says market data is disabled by default for non-FX instruments outside Saxo's own platforms, and that the client enables it in SaxoTraderGO and accepts a disclaimer. The retrieved disclaimer lists copying, reproduction, downloading, and distributing market data as misuse. The retrieved page did not add a separate sentence that names a written-permission form beyond that disclaimer and the separate market-data agreement above. Temporary caching is not given its own permission. Personal display inside the account holder's own tool is the personal-use article. Persistent historical storage is the private-storage article and stops at redistribution. Multi-user commercial display is not permitted on these pages.

Because any signed-in Google account can open Explore, Saxo prices stay out of `instruments`. Technical availability is verified. The primary slot stays unresolved for storage.

## Saxo

Saxo was retested on LIVE after the founder accepted market-data terms. The terms flag was true. Quotes were delayed and indicative, with no last. Chart pages returned closes and were not stored. Production OAuth stays off. This build does not enable trading. A chart close is not a last trade. The adapter can take a later licensed vendor.

## Refresh

`etf-refresh` and `etf-refresh-status` are separate from the 06:15 UTC macro workflow. The default provider is `unresolved`. Jobs are prices, NAV, holdings, and FX. Holdings automation stays blocked. FX stays a gap. Prices stay blocked while the primary slot is unresolved.
