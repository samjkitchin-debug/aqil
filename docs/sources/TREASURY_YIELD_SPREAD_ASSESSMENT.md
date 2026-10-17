# US Treasury 10y–3m yield spread — expansion assessment (M3)

Status: **blocked for implementation** pending licence and vintage clarity.

## Authoritative provider candidates

| Candidate | Dataset | Frequency | Vintage panel | Notes |
|-----------|---------|-----------|---------------|-------|
| US Treasury daily yield curve XML | Constant maturity yields (incl. 10y, 3m) | Daily | Not a formal ALFRED-style vintage store in this feed | `docs/sources/SOURCE_RIGHTS.csv` row `treasury_daily_yield_curve` — licence **unknown** |
| FRED DGS10 / TB3MS | Published series | Daily | ALFRED vintages exist on FRED | FRED UNRATE row marks **ineligible** for retention/AI; Treasury series need separate legal review before any adapter |

## Methodological reference

The 10-year minus 3-month Treasury spread is a widely cited recession-indicator input (e.g. Estrella–Mishkin literature). It is **not** interchangeable with Fiscal Data “average interest rates on Treasury securities” (monthly borrowing-cost statistics).

## Rights summary (as of 2026-10-17)

- Automated collection: **not permitted** until Treasury.gov XML terms are recorded and `automated_access` is explicitly permitted in `SOURCE_RIGHTS.csv`.
- Historical integrity: daily Treasury levels require explicit vintage strategy; latest-revised FRED snapshots must not be presented as historical point-in-time knowledge.
- AI processing: no adapter should send restricted Treasury payloads to an LLM.

## Recommended next step

Complete licence review for Treasury.gov yield-curve XML (or a clearly licensed FRED redistribution path), then add a fixture-backed adapter mirroring the BLS pattern before any live polling.
