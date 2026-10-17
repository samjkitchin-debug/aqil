-- pgTAP: forward schema security and immutability.
begin;

select plan(6);

select has_schema('forward');

insert into forward.catalyst_events (
  event_id, category, subject_type, subject_id, title, date_precision, status,
  source_id, first_observed_at, last_verified_at, payload
) values (
  'event:pgtap:immutable',
  'company_earnings',
  'company',
  'issuer:test',
  'Immutable scenario test event',
  'estimated',
  'scheduled',
  'fixture',
  timestamptz '2026-01-01 00:00:00+00',
  timestamptz '2026-01-01 00:00:00+00',
  '{}'::jsonb
);

insert into forward.forward_scenarios (
  scenario_id, event_id, frozen_at, payload, payload_hash
) values (
  'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  'event:pgtap:immutable',
  timestamptz '2026-01-01 00:00:00+00',
  '{"schema_version":"1.0"}'::jsonb,
  'abc'
);

select throws_ok(
  $$
    update forward.forward_scenarios
    set payload = '{"tampered": true}'::jsonb
    where scenario_id = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
  $$,
  'forward_scenarios are immutable after freeze'
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
