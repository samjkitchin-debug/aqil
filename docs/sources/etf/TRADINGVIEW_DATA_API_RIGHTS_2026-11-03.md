# TradingView Data API rights, 3 November 2026

Status: founder-only private research. This is not an exchange licence and it does not clear Explore for other signed-in users.

Terms read: https://www.tradingviewapi.com/terms/ (last updated 20 August 2026). Docs read: https://www.tradingviewapi.com/docs/.

## What the terms permit

Section 5 permits commercial use of the API, display in the customer's own product, redistribution of responses to that product's end users, and caching and forwarding. Caching is described as storing responses and proxying them through a backend. That is permission for the account holder to retain responses for private research.

Section 6 says the service is not affiliated with TradingView, Inc. and is not an exchange licence. Exchange and upstream rules can be stricter. A separate legal review is required before the data is shown to paying subscribers. Section 7 gives no indemnification.

## What Aqil will store

Validated daily observations may be stored for founder-only reads (`app_metadata.aqil_research = founder`). Raw responses are cached under `workers/research/.local/tradingview/`, which Git ignores. The credential is read from `TRADINGVIEW_API_KEY` in `workers/research/.env` or the process environment. It is sent only to `https://api.tradingviewapi.com` as `Authorization: Bearer`.

Redistribution to other signed-in users and commercial publication stay unknown. AI model training is prohibited for this source. The rights fragment is `docs/sources/etf/fragments/tradingview_data_api.csv`. It is not merged into `docs/sources/SOURCE_RIGHTS.csv`.

## Series

`GET /api/price/{symbol}` is the documented candlestick route. The fetched docs do not specify a separate `/api/price/ohlcv/{symbol}` series, so that path is not called. `POST /api/price/batch` is not used because the docs do not say that one batch call costs one quota unit.

Requests set `timeframe=D`, `type=Japanese`, and `adjustment=splits`. Omitting `type` would ask for Heikin-Ashi. The returned close is the adjusted series. It is stored as `adjusted_close` and is not copied into a raw close. `adjustment=dividends` is a different series (splits and cash dividends). The docs do not call it a total-return index.

Saxo remains a separate adapter. Saxo bars are not copied into `instruments`.

## Quota

The published Basic plan is 200 requests a month and 2 a second. This import hard-stops at 60 HTTP calls, including failures, with at most one request a second and one budgeted retry on HTTP 429. There is no production job and no browser code on this key.