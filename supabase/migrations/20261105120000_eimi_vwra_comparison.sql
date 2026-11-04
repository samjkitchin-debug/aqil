-- EIMI and VWRA comparison symbols.
-- The existing checks accept only VWRA, so an EIMI or matched-excess row cannot be stored.
-- Local only. Do not apply this file to a hosted project.
-- Same hosted prohibition as 20261104120000_historical_state_atlas.sql.
-- It does not edit LH-H-001 through the stored VWRA discovery claims.
-- It does not edit EVT-DEF-001 or EVT-DEF-002.
-- publication_allowed stays false.

alter table research.discovery_v2_trials drop constraint discovery_v2_trials_symbol;
alter table research.discovery_v2_trials add constraint discovery_v2_trials_symbol check (
  symbol in ('VWRA', 'EIMI', 'EIMI-VWRA', 'REGISTRY')
);

alter table research.discovery_v2_casebook drop constraint discovery_v2_casebook_symbol;
alter table research.discovery_v2_casebook add constraint discovery_v2_casebook_symbol check (
  symbol in ('VWRA', 'EIMI', 'EIMI-VWRA')
);

comment on constraint discovery_v2_trials_symbol on research.discovery_v2_trials is
  'VWRA remains the stored discovery. EIMI and the matched excess are later rows. REGISTRY is the method census.';
