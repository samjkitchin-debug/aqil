-- M5: extend forward evidence classes and collection audit trail.

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
  );

alter table forward.catalyst_events
  drop constraint catalyst_evidence_class;

alter table forward.catalyst_events
  add constraint catalyst_evidence_class check (
    evidence_class in (
      'verified_schedule',
      'verified_announcement',
      'curated_verified',
      'synthetic_demonstration'
    )
  );

alter table forward.forward_scenarios
  drop constraint scenario_evidence_class;

alter table forward.forward_scenarios
  add constraint scenario_evidence_class check (
    evidence_class in ('synthetic_demonstration', 'research_assessment')
  );

alter table forward.forward_scenarios
  drop constraint scenario_payload_labelled;

alter table forward.forward_scenarios
  add constraint scenario_payload_labelled check (
    coalesce(payload->>'evidence_class', evidence_class) in (
      'synthetic_demonstration',
      'research_assessment'
    )
  );

create table forward.collection_runs (
  run_id uuid primary key default gen_random_uuid(),
  source_id text not null,
  dataset_id text not null,
  collection_mode text not null,
  started_at timestamptz not null,
  finished_at timestamptz not null,
  outcome text not null,
  records_received integer not null default 0,
  records_new integer not null default 0,
  records_updated integer not null default 0,
  records_unchanged integer not null default 0,
  rights_record_id text not null,
  source_locator text,
  error_summary text,
  payload jsonb not null default '{}'::jsonb,
  constraint collection_mode_valid check (collection_mode in ('live', 'fixture')),
  constraint collection_outcome_valid check (
    outcome in ('completed', 'failed_rights', 'failed_fetch', 'failed_validation', 'partial')
  )
);

create index collection_runs_source_idx
  on forward.collection_runs (source_id, finished_at desc);

grant select, insert on forward.collection_runs to research_writer;

-- Live calendar refresh may update verification timestamps and recorded schedule revisions.
grant update on forward.catalyst_events to research_writer;

revoke all on forward.collection_runs from public;
revoke all on forward.collection_runs from anon;
revoke all on forward.collection_runs from authenticated;
revoke all on forward.collection_runs from service_role;
