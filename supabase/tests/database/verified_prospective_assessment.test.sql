-- Verified real-event scenarios stay immutable. Outcomes cannot claim forecasting skill.
begin;

select plan(3);

-- Constraint fixture only. This row does not verify the BLS publication calendar.
insert into forward.catalyst_events (
  event_id, category, subject_type, subject_id, title, scheduled_at, date_precision, status,
  source_id, source_locator, first_observed_at, last_verified_at, payload, evidence_class
) values (
  'bls:empsit:2026-10',
  'macro_release',
  'series',
  'LNS14000000',
  'October 2026 Employment Situation',
  timestamptz '2026-11-06 13:30:00+00',
  'confirmed',
  'scheduled',
  'bls_cps_unemployment_rate',
  'https://www.bls.gov/schedule/news_release/empsit.htm',
  timestamptz '2026-10-18 00:00:00+00',
  timestamptz '2026-10-18 00:00:00+00',
  '{"evidence_class":"verified_schedule"}'::jsonb,
  'verified_schedule'
);

insert into forward.forward_scenarios (
  scenario_id, event_id, frozen_at, payload, payload_hash, evidence_class
) values (
  'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
  'bls:empsit:2026-10',
  timestamptz '2026-10-18 00:20:00+00',
  '{"evidence_class":"verified_real_event","no_directional_forecast":"true"}'::jsonb,
  'pending',
  'verified_real_event'
);

select throws_ok(
  $$ update forward.forward_scenarios set payload_hash = 'changed' where scenario_id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd' $$,
  'P0001',
  'forward_scenarios are immutable after freeze',
  'a verified scenario cannot be overwritten'
);

select throws_ok(
  $$
    insert into forward.event_outcomes (
      event_id, scenario_id, observed_at, payload, content_hash, source_id, evidence_class
    ) values (
      'bls:empsit:2026-10',
      'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
      timestamptz '2026-11-06 13:31:00+00',
      '{"evidence_class":"verified_release_outcome","forecasting_skill":"accurate"}'::jsonb,
      'bad',
      'bls_cps_unemployment_rate',
      'verified_release_outcome'
    )
  $$,
  '23514',
  null,
  'an outcome cannot award forecasting skill'
);

select lives_ok(
  $$
    insert into forward.event_outcomes (
      event_id, scenario_id, observed_at, payload, content_hash, source_id, evidence_class
    ) values (
      'bls:empsit:2026-10',
      'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
      timestamptz '2026-11-06 13:31:00+00',
      '{"evidence_class":"verified_release_outcome","forecasting_skill":null}'::jsonb,
      'first',
      'bls_cps_unemployment_rate',
      'verified_release_outcome'
    )
  $$,
  'a first release outcome can omit a forecasting score'
);

select * from finish();
rollback;
