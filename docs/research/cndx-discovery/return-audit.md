# Return audit

Retrospective price description. This is not a total-return study and not a point-in-time signal. `publication_allowed` stays false. This record is not Verified.

## What is stored

The only stored market-price rows for these listings are split-adjusted closes. A split-adjusted close stays a split-adjusted close. It is not relabelled as a distribution-adjusted total return, an issuer net asset value, the Nasdaq-100 index, or an investor return after costs and foreign exchange.

| Ticker | MIC | Listing currency | ISIN | Distribution policy | Price currency | Quote | Price type | Adjustment | Sessions | First | Last |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| CNDX | XLON | USD | IE00B53SZB19 | accumulating | USD | USD | adjusted_close | adjusted | 2525 | 2016-11-03 | 2026-11-02 |
| VWRA | XLON | USD | IE00BK5BQT80 | accumulating | USD | USD | adjusted_close | adjusted | 1838 | 2019-07-25 | 2026-11-02 |

Both stored listings are US dollars on XLON. The matched comparison therefore uses common eligible sessions, the same adjustment convention, and US dollars. No foreign-exchange conversion is applied.

## What is absent

Issuer NAV rows in `instruments.nav_observations`: 0.
Share-class fund returns in `instruments.fund_returns`: 0.
Benchmark returns in `instruments.benchmark_returns`: 0.
Foreign-exchange rows in `instruments.fx_observations`: 0.

Stored price types across the market-price table:

- `adjusted_close` / `adjusted`: 42931 rows.

No rights-cleared official total-return or distribution series for these share classes is stored in the repository tables above. Saxo chart pages cited in the source notes were not written to `instruments` and are not used here. No new vendor file was downloaded. No Nasdaq-100 index history was constructed. No Singapore-dollar investor return was constructed.

## Gap

The bounded gap is the difference between a split-adjusted listing close and a distribution-adjusted total return, and between that close and an investor result after fund expenses and currency conversion. Both share classes are stored as accumulating. An accumulating class does not authorise adding a dividend on top of the close, and a price change alone is not stored as a total return. Until a rights-cleared total-return series is already in the repository, economic investment claims stay blocked. Exploratory research on the stored split-adjusted closes may proceed and must keep that label.

Common eligible sessions for a CNDX and VWRA comparison start on or after the later first stored session. VWRA's first stored session is 2019-07-25. CNDX sessions before its own first stored session are refused and are not filled.
