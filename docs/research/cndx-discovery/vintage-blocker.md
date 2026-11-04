# Vintage blocker

The single method inspected for a point-in-time replay is `SAHM_UNEMPLOYMENT_GAP`. Its only required dataset is `bls.ln.LNS14000000`. The registered dependency binds that series as `latest_revised`. The rule uses a three-month average and a 12-month lookback. `PERIOD_LEVEL_CHANGE` uses the same series and is not a second candidate for this note.

The stored BEA real-GDP vintage, `bea.vintage.real_gdp.pct_preceding`, is not an input of the 26 registered methods. It was not substituted.

ALFRED retention is prohibited. No ALFRED file was read and none was stored.

Stored provider-vintage rows for `bls.ln.LNS14000000`: 15, 2023-11-05 to 2025-01-05. Those rows are not an original-vintage lookback long enough to replay the Sahm average and the 12-month window. The current LN file has no vintage column. The Employment Situation archive may have been revised.

Blocker: the method cannot be replayed as point-in-time from a rights-cleared source already in the repository. Latest-revised unemployment was not relabelled as point-in-time. No new source was ingested. The search stops at this one method.

Registered gate assessment:

Gate 5 is blocked. 26 registered methods were inspected. Declared vintage classes: latest_revised. This pass does not relabel one. bea.vintage.real_gdp.pct_preceding is not a required input of any registered method. Live provider-vintage datasets on the preserved database: bea.vintage.real_gdp.pct_preceding. fred.alfred.UNRATE historical archiving is prohibited, so ALFRED is not stored. Unemployment, CPI-U, industrial production, and the H.15 Treasury yields are permitted to be archived as their current publications. Those publications are not original vintages. The Employment Situation archive and the CPI archive are also permitted to be archived, and the rights rows say those archived releases may have been revised. No rights-cleared source supplies an original vintage for every input of one registered method. No methodology and no vintage were manufactured.
