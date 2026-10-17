-- M5: company IR watchlist rows may record an unknown or estimated date
-- without claiming a verified schedule.

alter table forward.catalyst_events
  drop constraint catalyst_provenance_matches_evidence;

alter table forward.catalyst_events
  add constraint catalyst_provenance_matches_evidence check (
    (
      evidence_class = 'synthetic_demonstration'
      and source_locator like 'synthetic://%'
    )
    or (
      evidence_class = 'verified_schedule'
      and source_locator like 'https://%'
    )
    or (
      evidence_class = 'verified_announcement'
      and source_locator like 'https://%'
    )
    or (
      evidence_class = 'curated_verified'
      and coalesce(payload->>'provenance', '') = 'founder_curated'
    )
    or (
      evidence_class = 'watchlist_unverified'
      and source_locator like 'https://%'
      and date_precision in ('estimated', 'unknown')
      and coalesce(payload->>'date_status', '') in ('estimated', 'unknown')
    )
  );

alter table forward.catalyst_events
  drop constraint catalyst_evidence_class;

alter table forward.catalyst_events
  add constraint catalyst_evidence_class check (
    evidence_class in (
      'verified_schedule',
      'verified_announcement',
      'curated_verified',
      'watchlist_unverified',
      'synthetic_demonstration'
    )
  );
