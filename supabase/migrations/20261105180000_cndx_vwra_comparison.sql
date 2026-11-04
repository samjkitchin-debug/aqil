-- CNDX and VWRA comparison symbols.
-- The existing checks accept VWRA, EIMI, and the EIMI matched excess.
-- A CNDX row cannot be stored until those checks are widened.
-- Local only. Do not apply this file to a hosted project.
-- Same hosted prohibition as 20261104120000_historical_state_atlas.sql
-- and 20261105120000_eimi_vwra_comparison.sql.
-- It does not edit LH-H-001 through the stored EIMI comparison claims.
-- It does not edit EVT-DEF-001 or EVT-DEF-002.
-- publication_allowed stays false.

alter table research.discovery_v2_trials drop constraint discovery_v2_trials_symbol;
alter table research.discovery_v2_trials add constraint discovery_v2_trials_symbol check (
  symbol in ('VWRA', 'EIMI', 'EIMI-VWRA', 'REGISTRY', 'CNDX', 'CNDX-VWRA')
);

alter table research.discovery_v2_casebook drop constraint discovery_v2_casebook_symbol;
alter table research.discovery_v2_casebook add constraint discovery_v2_casebook_symbol check (
  symbol in ('VWRA', 'EIMI', 'EIMI-VWRA', 'CNDX', 'CNDX-VWRA')
);

comment on constraint discovery_v2_trials_symbol on research.discovery_v2_trials is
  'VWRA, EIMI, and CNDX discovery rows. REGISTRY is the method census. Matched excesses are separate symbols.';
