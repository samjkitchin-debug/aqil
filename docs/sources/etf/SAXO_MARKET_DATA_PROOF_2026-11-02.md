# Saxo market-data proof, 2 November 2026

## LIVE retest after terms acceptance

The founder accepted OpenAPI market-data terms in SaxoTraderGO. This section retests the earlier LIVE result. That earlier NoAccess and HTTP 403 result is not continuing evidence of unavailability.

At 2026-11-02T08:58:33Z the saved session environment was LIVE. The access token had expired and the refresh token was still valid, so the existing LIVE refresh path was used once. The refresh returned HTTP 201. No token was written into this note. A second read at 2026-11-02T08:59:56Z found the new access token still valid and did not refresh again. `GET /port/v1/users/me` on `https://gateway.saxobank.com/openapi` returned HTTP 200. `MarketDataViaOpenApiTermsAccepted` was true. The response was JSON, with Saxo rate-limit headers and no Akamai header.

The five London lines were read again with the UICs already confirmed by `GET /ref/v1/instruments/details/{Uic}/Etf`. Each details call returned HTTP 200, AssetType `Etf`, exchange `LSE_ETF`, currency `USD`, and a `:xlon` symbol. No TSX or NEO `CNDX` was attached.

`GET /trade/v1/infoprices` returned HTTP 200 for each. Price type bid and ask were `OldIndicative`. Delay was 15 minutes. Last was absent. This is a delayed indicative quote, not an executable quote and not a last trade. HTTP 200 with `NoAccess` would not have been success. This call was not `NoAccess`.

| Symbol | First read bid | First read ask | Repeat bid | Repeat ask | Last | Delay |
| --- | --- | --- | --- | --- | --- | --- |
| VWRA:xlon | 189.18 | 189.2 | 189.18 | 189.24 | absent | 15 |
| EIMI:xlon | 50.7 | 50.73 | 50.7 | 50.73 | absent | 15 |
| CNDX:xlon | 1644 | 1644.4 | 1644.2 | 1644.4 | absent | 15 |
| IUIT:xlon | 50.36 | 50.39 | 50.37 | 50.39 | absent | 15 |
| IWMO:xlon | 109.12 | 109.22 | 109.12 | 109.22 | absent | 15 |

`GET /chart/v3/charts?Horizon=1440&Count=1200` returned HTTP 200 for each. Each page had 1,200 samples with a close and no last. The earliest sample was 2022-02-01 and the latest was 2026-11-02. No HTTP 403 and no Akamai header. DataVersion was unchanged on the repeat. This page is the requested window, not proof of the full history. Older pages were not requested.

| Symbol | Bars | Earliest | Latest | DataVersion |
| --- | --- | --- | --- | --- |
| VWRA:xlon | 1200 | 2022-02-01 | 2026-11-02 | 29890383 |
| EIMI:xlon | 1200 | 2022-02-01 | 2026-11-02 | 29890675 |
| CNDX:xlon | 1200 | 2022-02-01 | 2026-11-02 | 29890544 |
| IUIT:xlon | 1200 | 2022-02-01 | 2026-11-02 | 29890694 |
| IWMO:xlon | 1200 | 2022-02-01 | 2026-11-02 | 29890902 |

No FxSpot UIC was on the allow-listed positions read. No FX UIC was guessed. Reference, indicative, and executable FX were not retrieved.

The published Saxo terms still separate private retention from redistribution. Accepting market-data terms is not permission to display prices to other users. `/explore` can be opened by any signed-in Google account, so these rows were not written to `instruments`. Gate E and Gate F are not passed. No schedule was run.



## Chart pagination, 2 November 2026, 09:12 UTC

The access token was still valid, so it was not refreshed. No price was stored. Each call was GET /chart/v3/charts on https://gateway.saxobank.com/openapi with AssetType=Etf, Horizon=1440, Count=1200, and FieldGroups=ChartInfo,Data. The older page used Mode=UpTo and Time equal to the earliest sample of the previous page. No page returned HTTP 403 or an empty refusal. Each series stopped when its earliest sample equalled ChartInfo.FirstSampleTime. That timestamp is Saxo's first chart sample. It is not a cited share-class inception. The sample dated 2026-11-02 is the current session and is not treated as a completed close. DataVersion matched the earlier retest.

| Symbol | UIC | FirstSampleTime | Pages | Counts | Older page refused |
| --- | --- | --- | --- | --- | --- |
| VWRA:xlon | 14464978 | 2019-07-29 | 2 | 1200 then 637 | no |
| EIMI:xlon | 969856 | 2014-06-11 | 3 | 1200, 1200, 707 | no |
| CNDX:xlon | 4937893 | 2010-09-15 | 3 | 1200, 1200, 1065 | no |
| IUIT:xlon | 4925949 | 2016-06-23 | 3 | 1200, 1200, 189 | no |
| IWMO:xlon | 4532733 | 2014-10-20 | 3 | 1200, 1200, 293 | no |

## Earlier notes

The sections below were written before this retest. They include the simulation token and the earlier LIVE NoAccess session. They are history.


**Decision: not suitable.** The supplied 24-hour token is a simulation token. `GET /port/v1/users/me` on `https://gateway.saxobank.com/openapi` returned HTTP 401. The same path on `https://gateway.saxobank.com/sim/openapi` returned HTTP 200, and no further LIVE call was made with it. Simulation returned numeric bid and ask quotes and daily bars. Those figures are delayed indicative simulation data, not a LIVE close, and they were not written to the database. Saxo is not suitable as a primary daily-close source.

## Supplied token, 08:36 UTC

The token was used only as a bearer header and was not stored. Retrieved at 2026-11-02T08:36:13.287Z.

`GET /port/v1/accounts/me` on simulation returned HTTP 200 with `IsTrialAccount: true`, currency `EUR`, and `Active: true`. `GET /root/v1/sessions/capabilities` returned HTTP 200:

```json
{ "AuthenticationLevel": "Authenticated", "DataLevel": "Standard", "TradeLevel": "OrdersOnly" }
```

`GET /port/v1/users/me` returned HTTP 200. `MarketDataViaOpenApiTermsAccepted` was `true` on this simulation user. Terms were not accepted or changed. `LegalAssetTypes` included `Stock` and `Etf`. That flag belongs to the simulation user. It does not change the LIVE account.

The ISIN keyword search returned the same London lines as the LIVE vault session. Details returned `AssetType` `Etf`. The ISIN string was not in the details body. No TSX or NEO `CNDX` was in the `IE00B53SZB19` result. The priced line is the London USD ticker.

| ISIN | UIC | AssetType | Symbol | Exchange | Currency |
| --- | --- | --- | --- | --- | --- |
| IE00BK5BQT80 | 14464978 | Etf | VWRA:xlon | LSE_ETF, London Stock Exchange (ETFs), GB | USD |
| IE00BKM4GZ66 | 969856 | Etf | EIMI:xlon | LSE_ETF, London Stock Exchange (ETFs), GB | USD |
| IE00B53SZB19 | 4937893 | Etf | CNDX:xlon | LSE_ETF, London Stock Exchange (ETFs), GB | USD |
| IE00B3WJKG14 | 4925949 | Etf | IUIT:xlon | LSE_ETF, London Stock Exchange (ETFs), GB | USD |
| IE00BP3QZ825 | 4532733 | Etf | IWMO:xlon | LSE_ETF, London Stock Exchange (ETFs), GB | USD |

`GET /trade/v1/infoprices` returned HTTP 200 for each. `Quote.ErrorCode` was `None`. Price type bid and ask were `OldIndicative`. Delay was 15 minutes. Last was absent. Timestamps were about 08:20–08:36 UTC. These are simulation broker quotes.

| Symbol | Bid | Ask | Mid | Last | Delay | Currency |
| --- | --- | --- | --- | --- | --- | --- |
| VWRA:xlon | 189.02 | 189.04 | 189.03 | absent | 15 | USD |
| EIMI:xlon | 50.67 | 50.7 | 50.685 | absent | 15 | USD |
| CNDX:xlon | 1644 | 1644.4 | 1644.2 | absent | 15 | USD |
| IUIT:xlon | 50.37 | 50.41 | 50.39 | absent | 15 | USD |
| IWMO:xlon | 109.03 | 109.16 | 109.095 | absent | 15 | USD |

`GET /chart/v3/charts?Horizon=1440&Count=1200` with those UICs and `AssetType=Etf` returned HTTP 200 for each. No error body. Each response contained 1200 bars, so the page cap was hit and older history was not requested. The earliest bar date in the returned page was 2022-02-01 and the latest was 2026-11-02. Chart delay was 15 minutes. `DataVersion` was 29884597 for VWRA, 29885235 for EIMI and CNDX, 29890007 for IUIT, and 29886063 for IWMO. The returned closes were numeric. No HTTP 403 occurred, so this token does not show an entitlement refusal or an edge-security block. Response headers were `content-type: application/json; charset=utf-8` and Saxo chart rate-limit headers. No Akamai header was present.

One FX read: simulation `EURUSD`, UIC 21, `AssetType` `FxSpot`, HTTP 200. Bid 1.1209, ask 1.1211, mid 1.121, delay 0, price type `Tradable`, `LastUpdated` 2026-11-02T08:36:17.000000Z. This is a simulation broker quote, not a reference fixing.

Endpoint success is not permission to store the prices. Nothing was inserted into the database.

## Earlier LIVE vault session

The local LIVE vault, used before this token, is a different environment. Its results are below. A simulation success does not replace them.

No bar was returned on that LIVE session. Each info-price call returned HTTP 200 with `PriceTypeBid` and `PriceTypeAsk` of `NoAccess`, and no bid, ask, or last.

The LIVE access token was unexpired at the start of those calls. It was not refreshed. Account settings, market-data terms, and trading permission were left unchanged. No order, transfer, withdrawal, or chart subscription was sent.

Calls ran from 2026-11-02T08:27:59.699Z. The stored LIVE access expiry was 2026-11-02T08:43:56.196Z and the stored refresh expiry was 2026-11-02T09:23:56.196Z. About 943 seconds of access lifetime remained when the first batch finished.

## How the instruments were resolved

`GET /ref/v1/instruments/details?Keywords={ISIN}` is allow-listed and returned HTTP 200. It ignored the ISIN. The first symbols for `IE00BK5BQT80` were `NVDA:xnas`, `NVD:xetr`, `NVDA:xmil`, `SPCX:xnas`, and `SPX:xetr`.

The ISIN keyword search `GET /ref/v1/instruments` is not allow-listed: `saxoReadUrl` returns null. This proof called that read-only reference search on the LIVE host anyway, because the details query cannot resolve an ISIN. The application would refuse it. Each search returned HTTP 200. The UIC used afterwards was confirmed with the allow-listed details call. No search row and no details body contained the ISIN string. Saxo’s published instrument-details schema has no ISIN field.

The ISINs were checked before mapping:

| Anchor | ISIN | Independent source | Saxo LSE line accepted |
| --- | --- | --- | --- |
| Vanguard FTSE All-World UCITS ETF accumulating | IE00BK5BQT80 | [etf.ie](https://etf.ie/ucits/) lists this ISIN for the accumulating FTSE All-World UCITS ETF | `VWRA:xlon`, description “Vanguard FTSE All-World UCITS Acc ETF” |
| iShares Core MSCI EM IMI UCITS ETF accumulating | IE00BKM4GZ66 | [etf.ie](https://etf.ie/ucits/) lists EIMI with this ISIN | `EIMI:xlon`, description “iShares Core MSCI EM IMI UCITS ETF” |
| iShares NASDAQ 100 UCITS ETF accumulating | IE00B53SZB19 | [Concorde Investments Ireland](https://www.ciireland.com/important-information/exchange-traded-funds/) lists iShares NASDAQ 100 UCITS ETF with this ISIN | `CNDX:xlon`, description “iShares NASDAQ 100 Acc UCITS ETF” |
| iShares S&P 500 Information Technology Sector UCITS ETF accumulating | IE00B3WJKG14 | [etf.ie](https://etf.ie/ucits/) lists this ISIN for that accumulating sector ETF | `IUIT:xlon`, description “iShares S&P 500 Info Technology Sector UCITS ETF” |
| iShares Edge MSCI World Momentum Factor UCITS ETF accumulating | IE00BP3QZ825 | [iShares UK](https://www.ishares.com/uk/individual/en/products/270051/ishares-msci-world-momentum-factor-ucits-etf) and [justETF](https://www.justetf.com/en/etf-profile.html?isin=IE00BP3QZ825) give this ISIN for the accumulating USD share class | `IWMO:xlon`, description “iShares Edge MSCI World Momentum Factor UCITS ETF” |

The same ISIN search also returned other listings of the same description, including `VWCE:xetr`, `VWRP:xlon` (GBP), `EMIM:xlon` (GBP), `IS3N:xetr`, `SXRV:xetr`, `CNX1:xlon`, `QDVE:xetr`, and `IWFM:xlon`. Those were not used for the price or chart call. The price call used the London line whose symbol is the common USD ticker. The `IE00B53SZB19` result contained no TSX or NEO row. No Canadian `CNDX` was attached.

## 1. Market-data terms and entitlements

`GET /port/v1/users/me` at 2026-11-02T08:29:47Z, HTTP 200. Response headers included `content-type: application/json; charset=utf-8`, `date: Mon, 02 Nov 2026 08:29:47 GMT` on the follow-up, and Saxo rate-limit headers. No Akamai header was present.

`MarketDataViaOpenApiTermsAccepted` was `false`. Terms were not accepted.

`LegalAssetTypes` reported `Stock` and `Etf`, and also `FxSpot`, `FxForwards`, `FxVanillaOption`, `ContractFutures`, `FuturesStrategy`, `StockOption`, `Bond`, `FuturesOption`, `StockIndexOption`, `Cash`, `CfdOnStock`, `CfdOnIndex`, `CfdOnFutures`, `StockIndex`, `MutualFund`, `CfdOnEtf`, `CfdOnEtc`, `CfdOnEtn`, `CfdOnFund`, `CfdOnRights`, `CfdOnCompanyWarrant`, `Etc`, `Etn`, `Fund`, `FxSwap`, `Rights`, `IpoOnStock`, and `CompanyWarrant`.

`GET /port/v1/accounts/me` returned HTTP 200 with `IsTrialAccount: false`, currency `SGD`, and `Active: true`. This is the LIVE account. `LegalAssetTypes` names the asset types the account may trade. It is not the OpenAPI market-data grant.

## 2. Asset type

Every accepted details response returned the exact string `Etf`. None of these five returned legacy `Stock`.

## 3. Identity

Allow-listed `GET /ref/v1/instruments/details/{Uic}/{AssetType}`, each HTTP 200. The ISIN was not in the body.

| ISIN | UIC | AssetType | Symbol | ExchangeId | Exchange | Country | Currency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IE00BK5BQT80 | 14464978 | Etf | VWRA:xlon | LSE_ETF | London Stock Exchange (ETFs) | GB | USD |
| IE00BKM4GZ66 | 969856 | Etf | EIMI:xlon | LSE_ETF | London Stock Exchange (ETFs) | GB | USD |
| IE00B53SZB19 | 4937893 | Etf | CNDX:xlon | LSE_ETF | London Stock Exchange (ETFs) | GB | USD |
| IE00B3WJKG14 | 4925949 | Etf | IUIT:xlon | LSE_ETF | London Stock Exchange (ETFs) | GB | USD |
| IE00BP3QZ825 | 4532733 | Etf | IWMO:xlon | LSE_ETF | London Stock Exchange (ETFs) | GB | USD |

Details headers were Saxo application headers: `content-type: application/json; charset=utf-8`, `x-correlation`, and `x-ratelimit-refdatainstrumentsminute-limit: 60`. No server or Akamai header was present.

## 4. Info prices

`GET /trade/v1/infoprices` with `FieldGroups=Quote,PriceInfo,PriceInfoDetails,DisplayAndFormat,InstrumentPriceDetails`. All five returned HTTP 200. The shape was the same for each. Representative body for `VWRA:xlon`, retrieved `Mon, 02 Nov 2026 08:28:01 GMT`:

```json
{
  "AssetType": "Etf",
  "DisplayAndFormat": { "Currency": "USD", "Symbol": "VWRA:xlon" },
  "LastUpdated": "0001-01-01T00:00:00.000000Z",
  "PriceSource": "LSE_ETF",
  "Quote": {
    "Amount": 0,
    "ErrorCode": "None",
    "PriceSource": "LSE_ETF",
    "PriceSourceType": "Firm",
    "PriceTypeAsk": "NoAccess",
    "PriceTypeBid": "NoAccess"
  },
  "Uic": 14464978
}
```

| ISIN | Symbol | HTTP | Bid | Ask | Last | Delay | Currency | Timestamp | Price type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IE00BK5BQT80 | VWRA:xlon | 200 | absent | absent | absent | absent | USD | 0001-01-01T00:00:00.000000Z | NoAccess |
| IE00BKM4GZ66 | EIMI:xlon | 200 | absent | absent | absent | absent | USD | 0001-01-01T00:00:00.000000Z | NoAccess |
| IE00B53SZB19 | CNDX:xlon | 200 | absent | absent | absent | absent | USD | 0001-01-01T00:00:00.000000Z | NoAccess |
| IE00B3WJKG14 | IUIT:xlon | 200 | absent | absent | absent | absent | USD | 0001-01-01T00:00:00.000000Z | NoAccess |
| IE00BP3QZ825 | IWMO:xlon | 200 | absent | absent | absent | absent | USD | 0001-01-01T00:00:00.000000Z | NoAccess |

`Quote.ErrorCode` was `None` and `PriceSourceType` was `Firm`. Relevant headers included `content-type: application/json; charset=utf-8` and `x-ratelimit-tradeinfopricesminute-limit: 120`. A chart close was not used as a quote.

## 5. Daily charts

`GET /chart/v3/charts?Horizon=1440&Count=1200&FieldGroups=ChartInfo,Data,DisplayAndFormat` with the UIC and `AssetType=Etf` above. Each first page returned HTTP 403. No second page was requested. Count is 0. There is no earliest bar, no latest bar, and no `DataVersion`.

| ISIN | HTTP | Bars | Earliest | Latest | DataVersion |
| --- | --- | --- | --- | --- | --- |
| IE00BK5BQT80 | 403 | 0 | none | none | absent |
| IE00BKM4GZ66 | 403 | 0 | none | none | absent |
| IE00B53SZB19 | 403 | 0 | none | none | absent |
| IE00B3WJKG14 | 403 | 0 | none | none | absent |
| IE00BP3QZ825 | 403 | 0 | none | none | absent |

## 6. The HTTP 403 is an entitlement refusal

Reproduced on 2 November 2026 for every chart call. Representative headers for `EIMI:xlon` at `Mon, 02 Nov 2026 08:29:47 GMT`:

- `content-type: application/json; charset=utf-8`
- `content-length: 63`
- `x-correlation: 56d00813c63141b18f3651871560929d#5580#4df867f7-8c0e-47a2-9650-184c87ddc05c#721`
- `x-ratelimit-chartminute-limit: 120`
- `x-ratelimit-chartminute-remaining: 119`
- `x-ratelimit-chartminute-reset: 60`

No `server` header and no Akamai header were present. The body was:

```json
{ "ErrorCode": "None", "Message": "Access denied." }
```

The same JSON body was returned for the other four charts. A JSON body, Saxo’s chart rate-limit headers, and the user field `MarketDataViaOpenApiTermsAccepted: false` identify an application entitlement refusal. An Akamai edge rejection would be a different content type and would carry an edge server header. This response is the entitlement refusal.

## 7. FX

No FX call was made. `GET /port/v1/positions/me` returned HTTP 200 and contained no `FxSpot` UIC. `GET /trade/v1/infoprices` and `GET /chart/v3/charts` can carry `AssetType=FxSpot`, and those would be broker quotes rather than a reference fixing. No other FX history or reference-rate path is allow-listed, and none was added. The gap remains.

## 8. Later daily read

The current vault can authorise another LIVE read only until the stored refresh expiry, 2026-11-02T09:23:56.196Z. The access token and the refresh token are 40 minutes apart. These GETs do not need a trading-permission change: the calls were made without requesting one.

Saxo’s session note says renewing an authorisation token keeps the same session. Saxo’s security note says a successful refresh replaces and invalidates the previous refresh token. The existing in-process path does that and persists the new pair. It was not used, because the access token was still valid. After 09:23 UTC this vault cannot read again until the account holder signs in through the local LIVE flow. It cannot support an unattended daily read on a later day. Production Connect Saxo was not enabled.

## 9. Published terms

A successful endpoint would not be permission to store prices. No price was returned in this proof. The terms still do not allow the product to keep them.

Saxo Bank Support, “Can I store and use OpenAPI market data for my own algo or AI/backtesting?”, updated 5 October 2026, <https://openapi.help.saxo/hc/en-us/articles/39663625431581-Can-I-store-and-use-OpenAPI-market-data-for-my-own-algo-or-AI-backtesting>:

> You may store the real-time market data you receive through OpenAPI and use it for your own private purposes, including automated backtesting, strategy validation, and AI/algo development, as long as you do not redistribute it.
>
> There is no fixed retention limit for private, non-redistributed use.
>
> You cannot redistribute the data in any form. This includes sharing, reselling, publishing, syndicating, or displaying it to other end users through a product, service, or application you provide to others.

The developer-portal disclaimer at <https://developer.saxobank.com/excel/user-guide/enabling-market-data> still lists copying, reproduction, downloading, and distributing market data as misuse. Private retention for the account holder is described as allowed. Writing prices into Aqil’s instrument store, or displaying them to other users, is redistribution. Prices from this source must not be written to instruments.

## 10. What would have to change

1. The account holder enables OpenAPI market data in SaxoTraderGO and accepts the terms there. This proof did not do that. Until `MarketDataViaOpenApiTermsAccepted` is true, the observed result is `NoAccess` on info prices and HTTP 403 on charts.
2. Leave the current access token in place until 2026-11-02T08:43:56.196Z. Refresh only after that, and only before 2026-11-02T09:23:56.196Z, through the existing one-process path. Do not request `FullTradingAndChat`.
3. The application still cannot resolve an ISIN: the allow-listed details query ignores `Keywords`, and the keyword search is refused by the guard.
4. Keep any later prices out of `instruments` unless a rights decision allows that product use.

**Suitability:** not suitable. The LIVE session was usable and the five London UCITS lines resolved as `Etf`, but every info price was `NoAccess` with no bid, ask, or last, and every daily chart was an entitlement HTTP 403 with no bar.
