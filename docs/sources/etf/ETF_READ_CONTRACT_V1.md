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

No vendor is the primary price source. The adapter registry slot is `unresolved` because `docs/sources/etf/SAXO_MARKET_DATA_PROOF_2026-11-02.md` is absent. EODHD and Twelve Data remain replaceable adapters. They are not selected. Nothing was purchased. No Saxo price was invented. Gate E is not passed.

The 2 November 2026 price-provider probe retrieved no London or Xetra bar. That note is evidence of those calls. It is not a vendor choice.

Rights rows `eodhd_global_etf_eod`, `twelve_data_global_etf_eod`, `mas_sgd_reference_fx`, and `saxo_sim_infoprices` are disabled and unknown. They are not permission. `vanguard_uk_vwra_holdings` and `ishares_ucits_holdings` stay prohibited.

The founder approval still required is not a purchase. Do not approve a subscription to EODHD, Twelve Data, or any other feed as the primary source. The primary slot stays unresolved until the Saxo proof file records all three of these facts: InfoPrices entitled, daily charts entitled, and retention permitted. If that file records them, Saxo may occupy the slot. A later licensed vendor can replace Saxo without changing share-class identity, this read contract, or the React pages. Close, NAV, bid, ask, last, and adjusted close stay distinct. Production display to any signed-in Google account still needs a retention and display right that matches that audience. That right is not recorded.

## Saxo

Saxo can be the primary price source only when the proof file records the three facts above. Production OAuth stays off. This build does not enable trading. HTTP 403 does not store a quote, does not invent a bar, and does not by itself select another vendor. A chart close is not the current quote.

## Refresh

`etf-refresh` and `etf-refresh-status` are separate from the 06:15 UTC macro workflow. The default provider is `unresolved`. Jobs are prices, NAV, holdings, and FX. Holdings automation stays blocked. FX stays a gap. Prices stay blocked while the primary slot is unresolved.
