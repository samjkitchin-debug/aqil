-- pgTAP: forward schema security, provenance, and immutability.
begin;

select plan(15);

select has_schema('forward');

insert into forward.catalyst_events (
  event_id, category, subject_type, subject_id, title, date_precision, status,
  source_id, source_locator, first_observed_at, last_verified_at, payload, evidence_class
) values (
  'event:pgtap:immutable',
  'company_earnings',
  'company',
  'issuer:test',
  'Immutable scenario test event',
  'estimated',
  'scheduled',
  'fixture',
  'synthetic://aqil/pgtap/event',
  timestamptz '2026-01-01 00:00:00+00',
  timestamptz '2026-01-01 00:00:00+00',
  '{"evidence_class":"synthetic_demonstration"}'::jsonb,
  'synthetic_demonstration'
);

insert into forward.forward_scenarios (
  scenario_id, event_id, frozen_at, payload, payload_hash, evidence_class
) values (
  'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  'event:pgtap:immutable',
  timestamptz '2026-01-01 00:00:00+00',
  '{"schema_version":"1.0","evidence_class":"synthetic_demonstration"}'::jsonb,
  'abc',
  'synthetic_demonstration'
);

select throws_ok(
  $$
    update forward.forward_scenarios
    set payload = '{"tampered": true}'::jsonb
    where scenario_id = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
  $$,
  'P0001',
  'forward_scenarios are immutable after freeze',
  'frozen scenarios cannot be updated'
);

select throws_ok(
  $$
    insert into forward.catalyst_events (
      event_id, category, subject_type, subject_id, title, date_precision, status,
      source_id, source_locator, first_observed_at, last_verified_at, payload, evidence_class
    ) values (
      'event:pgtap:bad-provenance',
      'central_bank_meeting',
      'macro',
      'economy:us',
      'Mismatched schedule',
      'estimated',
      'scheduled',
      'federal_reserve_fomc_calendar',
      'synthetic://aqil/pgtap/not-a-fed-source',
      timestamptz '2026-01-01 00:00:00+00',
      timestamptz '2026-01-01 00:00:00+00',
      '{}'::jsonb,
      'verified_schedule'
    );
  $$,
  '23514',
  null,
  'verified schedule cannot use a synthetic locator or an unconfirmed date'
);

select throws_ok(
  $$
    insert into forward.etf_holdings_snapshots (
      etf_id, as_of_date, retrieved_at, completeness, source_id, source_locator,
      payload, content_hash, evidence_class
    ) values (
      'etf:pgtap',
      '2025-06-30',
      timestamptz '2026-01-01 00:00:00+00',
      'top_holdings_partial',
      'pretend_provider',
      'synthetic://aqil/pgtap/weights',
      '{"evidence_class":"provider_holdings"}'::jsonb,
      'bad-hash',
      'provider_holdings'
    );
  $$,
  '23514',
  null,
  'synthetic locator cannot be stored as provider holdings'
);

insert into forward.etf_holdings_snapshots (
  etf_id, as_of_date, retrieved_at, completeness, source_id, source_locator,
  payload, content_hash, evidence_class
) values (
  'etf:pgtap',
  '2025-06-30',
  timestamptz '2026-01-01 00:00:00+00',
  'top_holdings_partial',
  'fixture',
  'synthetic://aqil/pgtap/weights',
  '{"evidence_class":"synthetic_demonstration"}'::jsonb,
  'same-hash',
  'synthetic_demonstration'
);

select throws_ok(
  $$
    insert into forward.etf_holdings_snapshots (
      etf_id, as_of_date, retrieved_at, completeness, source_id, source_locator,
      payload, content_hash, evidence_class
    ) values (
      'etf:pgtap',
      '2025-06-30',
      timestamptz '2026-02-01 00:00:00+00',
      'top_holdings_partial',
      'fixture',
      'synthetic://aqil/pgtap/weights',
      '{"evidence_class":"synthetic_demonstration"}'::jsonb,
      'same-hash',
      'synthetic_demonstration'
    );
  $$,
  '23505',
  null,
  'identical holdings content is rejected as a duplicate import'
);

select throws_ok(
  $$
    insert into forward.forward_scenarios (
      scenario_id, event_id, frozen_at, payload, payload_hash
    ) values (
      'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
      'event:pgtap:immutable',
      timestamptz '2026-01-01 00:00:00+00',
      '{"schema_version":"1.0","evidence_class":"verified_schedule"}'::jsonb,
      'unlabelled'
    );
  $$,
  '23514',
  null,
  'scenarios must use allowed evidence classes'
);

set local role anon;
select throws_ok(
  $$ select 1 from forward.catalyst_events limit 1 $$,
  '42501',
  null,
  'anon cannot read forward catalysts'
);
reset role;

set local role authenticated;
select throws_ok(
  $$ select 1 from forward.catalyst_events limit 1 $$,
  '42501',
  null,
  'authenticated cannot read forward catalysts'
);
reset role;

set local role service_role;
select throws_ok(
  $$ select 1 from forward.forward_scenarios limit 1 $$,
  '42501',
  null,
  'service_role cannot read forward scenarios'
);
reset role;

select ok(
  not has_schema_privilege('service_role', 'forward', 'USAGE'),
  'service_role has no usage on the forward schema'
);

select ok(
  not has_table_privilege('service_role', 'forward.forward_scenarios', 'SELECT'),
  'service_role is not granted select on forward scenarios'
);

select ok(
  not has_table_privilege('service_role', 'forward.catalyst_events', 'INSERT'),
  'service_role is not granted insert on forward catalysts'
);

select ok(
  not has_table_privilege('service_role', 'forward.etf_holdings_snapshots', 'SELECT'),
  'service_role is not granted select on holdings snapshots'
);

select ok(
  has_table_privilege('research_writer', 'forward.catalyst_events', 'INSERT'),
  'research_writer can insert catalysts'
);

select ok(
  has_table_privilege('research_writer', 'forward.catalyst_events', 'SELECT'),
  'research_writer can select catalysts'
);

select * from finish();
rollback;
