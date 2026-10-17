# M5 Grok High review package — live forward intelligence

**Branch:** `m5/live-intelligence-coverage`  
**PR:** https://github.com/samjkitchin-debug/aqil/pull/9  
**Scope:** Real macro calendar ingestion, frozen pre-event assessments, horizon export, founder-only web surfaces. No hosted migration apply, no live schedules, no paid data.

## What is genuinely sourced today

| Dataset | Source | Evidence class | Automated collect |
|---------|--------|----------------|-------------------|
| FOMC schedule | federalreserve.gov FOMC calendar | `verified_schedule` | Opt-in `--live` + fixture CI |
| BLS Employment Situation schedule | bls.gov empsit schedule | `verified_schedule` | Opt-in + fixture CI |
| BLS selected releases ICS | bls.ics | `verified_schedule` | Opt-in + fixture CI |
| BEA news schedule | bea.gov/news/schedule | `verified_schedule` | Opt-in + fixture CI |
| SEC completed filings | data.sec.gov submissions | `verified_announcement` (live) | Requires `AQIL_SEC_USER_AGENT` |
| Company IR watchlist | Curated JSON | `watchlist_unverified` / `curated_verified` | Manual register only |
| VWRA / iShares holdings | — | — | **Prohibited/disabled** automated; manual import gated |

## Vertical slice (macro)

1. `collect-forward --source fed-fomc --fixture …` → `forward.catalyst_events`
2. `sync-forward-intelligence --export apps/web/.local/forward-horizon.v1.json` → freezes `research_assessment` scenarios → exports bundle
3. Web loads `.local/` or `FORWARD_HORIZON_PATH` (founder auth) → Today / Calendar / Research

Integration proof: `workers/research/tests/test_forward_macro_vertical_slice.py` (requires local Supabase).

Web contract: `apps/web/fixtures/forward-horizon-verified-macro.v1.json` + `forward-horizon-verified-export.test.ts`.

## What remains synthetic

- M4 MSFT earnings demo path (`forward-demo`, `forward-horizon.v1.json` demo fixture)
- VWRA weights in demo bundle unless founder imports authorised holdings JSON
- No analyst consensus or market-implied expectations

## Rights decisions (summary)

- Vanguard Ireland terms: **automated_access prohibited**; internal retention via manual import only with `internal_retention_authorized` for `provider_holdings`
- iShares: source **disabled**
- SEC: completed filings only; **no forward earnings calendar inference**

## Operator commands

```bash
cd workers/research
uv run aqil-research collect-forward --source fed-fomc --fixture tests/fixtures/forward/fed_fomc_calendar_snippet.html
uv run aqil-research collect-forward --source sec-filings --fixture fixtures/forward/sec_submissions_sample.json
uv run aqil-research sync-forward-intelligence --export ../../apps/web/.local/forward-horizon.v1.json
uv run aqil-research forward-coverage
```

## Review questions for Grok High

1. Are FOMC/BLS/BEA schedule rights rows sufficient for private retention and internal research UI?
2. Is the `research_assessment` freeze discipline adequate to prevent look-ahead?
3. Should `provider_holdings` manual import require additional legal evidence fields beyond `internal_retention_authorized`?
