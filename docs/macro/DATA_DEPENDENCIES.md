# Data dependencies for the methodology programme

**Status:** canonical for which series the macro methods need  
**Owner:** founder  
**Last verified:** 25 October 2026  
**Counts:** read-only query of local database `postgres` on 25 October 2026. The hosted project was not queried.

This file links a dataset to the method that needs it. It is not a collection wave.

## Store, as queried

| Fact | Result |
|------|--------|
| Observation rows | 35,735 |
| Live retrievals | 35,648 |
| Fixture retrievals | 87 |
| `latest_revised` | 35,720 |
| `provider_vintage` | 15 |
| Distinct dataset identifiers | 24 |
| Operational dataset identifiers with live rows | 23 |
| Live rows on those 23, equal to distinct periods | 34,859 |
| OECD rows | 789, not operational |
| `research.research_runs` | 25 |
| `fed.g17.IP.B50001.S` | 1,293 `latest_revised` months, 1919-01-01 to 2026-09-01, one row per month |

The coverage register's period counts match that operational total. Fixture rows sit on dataset identifiers that are also used for live data. A method must select live retrievals, not the fixture unemployment rows.

All operational live rows are `latest_revised`. Point-in-time reconstruction is not available for them.

## Pilot: monthly Bry–Boschan

| Requirement | Held? |
|-------------|-------|
| Monthly seasonally adjusted industrial production, US | Yes. `fed.g17.IP.B50001.S`, Federal Reserve G.17, index, monthly |
| History long enough for several cycles | Yes, from January 1919 on the revised file |
| Vintage panel | No. Retrospective dating only |
| Extra series | No |

Do not substitute euro-area industrial production for this pilot. Do not aggregate the monthly index to quarters in order to run Harding–Pagan.

## Milestone: Stock–Watson 1989 coincident index

The 1989 chapter, page 359 of the NBER text, bases the proposed coincident index on four series from 1959:1, in log differences:

1. Industrial production, CITIBASE `IP` (BCD 47). G.17 total index `fed.g17.IP.B50001.S` is a candidate only. It is not confirmed as that 1989 series.
2. Real personal income less transfer payments, CITIBASE `GMYXP8` (BCD 51). Not stored. No rights row. The BEA row is a release calendar.
3. Real manufacturing and trade sales, CITIBASE `MT82` (BCD 57). Not stored. Advance durable-goods new orders are not this series.
4. Employee-hours in non-agricultural establishments, CITIBASE `LPMHU`. Not stored. Payroll employment `bls.ce.CES0000000001` is a headcount, not hours. The chapter says Commerce used employees and Stock–Watson followed Moore in using hours. A headcount is not a silent substitute.

No FRED or ALFRED path is used. AQ-102 stays blocked until GMYXP8, MT82, and LPMHU have rights rows and stored series, and until the Kalman matrices are transcribed from a clean source.

US GDP is not an input to that coincident index. It is also not stored, which blocks a US GDP nowcast.

Unemployment `bls.ln.LNS14000000` has 44 live months from 2023-01. It is not one of the four 1989 coincident series. Backfill it only if a later chosen specification requires it (`AQ-103`).

`AQ-101` must either adopt this four-series specification and list the three missing series with providers and rights, or adopt a different published Stock–Watson specification and list that specification's series. Until then, no estimation code.

## Other methods, only where the gap changes a decision

| Method | Held and relevant | Missing for the usual published form |
|--------|-------------------|--------------------------------------|
| Diffusion / PCA | G.17 and payrolls are long. CPI is long. Joint use with unemployment is limited by 44 months | A written panel. Not a reason to collect a region |
| Mixed-frequency nowcast of US GDP | Nothing that is US GDP | US GDP and its monthly indicators, plus vintages before a real-time claim |
| Euro-area nowcast, not selected | Quarterly real GDP, IP, unemployment, retail volume, HICP | A decision to make this the target, and a vintage policy |
| Yield-curve probit | `fed.h15.RIFLGFCY10_N.M` | A three-month Treasury yield. Do not subtract the federal funds rate and call it the Estrella–Mishkin spread (`AQ-104`) |
| BIS credit-to-GDP gap | `bis.ws_gli.Q.USD.3P.N.A.I.B.USD` is a dollar credit stock outside the US | The BIS credit-to-GDP gap series itself, and GDP |
| NFCI, excess bond premium | Nothing matching those inputs | Rights-cleared financial series named by the method |
| Trimmed-mean inflation | CPI-U all-items index | Component price indexes |
| Sahm rule, already implemented | Unemployment, short live sample | A longer unemployment history if the rule is to be studied before 2023. Not required for the Bry–Boschan pilot |

OECD G20 CLI is an institutional leading indicator already stored without rights clearance. It is not an input to the pilot or to the 1989 coincident specification, and it is not a Stock–Watson model.

## Rights

Every new series needs a `docs/sources/SOURCE_RIGHTS.csv` row before ingest. FRED/ALFRED stays ineligible. Do not import a blocked series through another vendor to avoid that row.

## Vintage policy for the first two methods

The pilot's runs are `latest_revised` retrospective calculations. The dynamic factor model may be estimated on revised data for numerical checks. Neither result is a real-time historical forecast until vintages exist. Candidate later sources are ALFRED, if rights change, and Philadelphia Fed real-time data. Neither is approved here.
