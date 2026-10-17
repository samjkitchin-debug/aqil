-- pgTAP: research schema integrity, temporal rules, conflicts and role privileges.
begin;

select plan(27);

-- ---------------------------------------------------------------------------
-- Fixtures (as superuser / postgres)
-- ---------------------------------------------------------------------------

insert into research.source_retrievals (
  retrieval_id,
  source_id,
  dataset_id,
  rights_record_id,
  provider_id,
  adapter_id,
  adapter_version,
  retrieved_at,
  collection_mode,
  endpoint_host
)
values (
  '11111111-1111-4111-8111-111111111111',
  'bls_cps_unemployment_rate',
  'bls.ln.LNS14000000',
  'bls_cps_unemployment_rate',
  'bls',
  'fixture_bls_ln_csv',
  '1.0.0',
  timestamptz '2025-02-01 12:00:00+00',
  'fixture',
  'api.bls.gov'
);

insert into research.source_retrievals (
  retrieval_id,
  source_id,
  dataset_id,
  rights_record_id,
  provider_id,
  adapter_id,
  adapter_version,
  retrieved_at,
  collection_mode
)
values (
  '22222222-2222-4222-8222-222222222222',
  'other_source',
  'other.dataset',
  'other_source',
  'other',
  'fixture_other',
  '1.0.0',
  timestamptz '2025-02-01 12:00:00+00',
  'fixture'
);

-- ---------------------------------------------------------------------------
-- Temporal integrity
-- ---------------------------------------------------------------------------

select throws_ok(
  $$
    insert into research.economic_observations (
      observation_id, retrieval_id, dataset_id, provider_id, source_id, rights_record_id,
      period_start, frequency, geography, unit, seasonal_adjustment, raw_value,
      quality_status, series_provenance, provider_vintage_date,
      source_release_at, earliest_model_available_at, availability_precision,
      retrieved_at, first_seen_at, adapter_version, release_identity_key
    ) values (
      'obs-ts-backdate',
      '11111111-1111-4111-8111-111111111111',
      'bls.ln.LNS14000000', 'bls', 'bls_cps_unemployment_rate', 'bls_cps_unemployment_rate',
      date '2024-01-01', 'monthly', 'US', 'percent', 'seasonally_adjusted', '3.7',
      'observed', 'provider_vintage', date '2024-02-01',
      timestamptz '2024-07-05 12:30:00+00',
      timestamptz '2019-01-02 00:00:00+00',
      'timestamp',
      timestamptz '2025-02-01 12:00:00+00',
      timestamptz '2025-02-01 12:00:00+00',
      'adapter:1',
      '2024-07-05 12:30:00+00'
    )
  $$,
  '23514',
  null,
  'timestamp earliest_model_available_at cannot precede source_release_at'
);

select throws_ok(
  $$
    insert into research.economic_observations (
      observation_id, retrieval_id, dataset_id, provider_id, source_id, rights_record_id,
      period_start, frequency, geography, unit, seasonal_adjustment, raw_value,
      quality_status, series_provenance, provider_vintage_date,
      source_release_at, availability_precision,
      retrieved_at, first_seen_at, adapter_version, release_identity_key
    ) values (
      'obs-date-backdate',
      '11111111-1111-4111-8111-111111111111',
      'bls.ln.LNS14000000', 'bls', 'bls_cps_unemployment_rate', 'bls_cps_unemployment_rate',
      date '2024-05-01', 'monthly', 'US', 'percent', 'seasonally_adjusted', '3.7',
      'observed', 'provider_vintage', date '2024-06-15',
      timestamptz '2024-07-05 12:30:00+00',
      'date',
      timestamptz '2025-02-01 12:00:00+00',
      timestamptz '2025-02-01 12:00:00+00',
      'adapter:1',
      '2024-07-05 12:30:00+00'
    )
  $$,
  '23514',
  null,
  'date-derived availability cannot precede source_release_at'
);

select lives_ok(
  $$
    insert into research.economic_observations (
      observation_id, retrieval_id, dataset_id, provider_id, source_id, rights_record_id,
      period_start, frequency, geography, unit, seasonal_adjustment, raw_value,
      quality_status, series_provenance, provider_vintage_date,
      source_release_at, availability_precision,
      retrieved_at, first_seen_at, adapter_version, release_identity_key
    ) values (
      'obs-date-ok',
      '11111111-1111-4111-8111-111111111111',
      'bls.ln.LNS14000000', 'bls', 'bls_cps_unemployment_rate', 'bls_cps_unemployment_rate',
      date '2024-05-01', 'monthly', 'US', 'percent', 'seasonally_adjusted', '3.7',
      'observed', 'provider_vintage', date '2024-07-06',
      timestamptz '2024-07-05 12:30:00+00',
      'date',
      timestamptz '2025-02-01 12:00:00+00',
      timestamptz '2025-02-01 12:00:00+00',
      'adapter:1',
      '2024-07-05 12:30:00+00'
    )
  $$,
  'date precision passes when derived availability is after source_release_at'
);

-- ---------------------------------------------------------------------------
-- Source / retrieval consistency
-- ---------------------------------------------------------------------------

select throws_ok(
  $$
    insert into research.economic_observations (
      observation_id, retrieval_id, dataset_id, provider_id, source_id, rights_record_id,
      period_start, frequency, geography, unit, seasonal_adjustment, raw_value,
      quality_status, series_provenance, provider_vintage_date,
      availability_precision, retrieved_at, first_seen_at, adapter_version, release_identity_key
    ) values (
      'obs-wrong-dataset',
      '11111111-1111-4111-8111-111111111111',
      'wrong.dataset', 'bls', 'bls_cps_unemployment_rate', 'bls_cps_unemployment_rate',
      date '2024-02-01', 'monthly', 'US', 'percent', 'seasonally_adjusted', '3.7',
      'observed', 'latest_revised', date '2024-02-01',
      'unknown',
      timestamptz '2025-02-01 12:00:00+00',
      timestamptz '2025-02-01 12:00:00+00',
      'adapter:1',
      '2025-02-01 12:00:00+00'
    )
  $$,
  'P0001',
  null,
  'observation dataset must match retrieval'
);

-- ---------------------------------------------------------------------------
-- Conflict handling (append-only, no overwrite)
-- ---------------------------------------------------------------------------

select results_eq(
  $$
    select status::text, observation_id
    from research.try_insert_observation(
      'obs-conflict-a',
      '11111111-1111-4111-8111-111111111111',
      'bls.ln.LNS14000000', 'bls', 'bls_cps_unemployment_rate', 'bls_cps_unemployment_rate',
      date '2024-03-01', null, 'monthly', 'US', 'percent', 'seasonally_adjusted',
      '3.7', 'observed', 'latest_revised', date '2024-02-01',
      null, null, 'unknown',
      timestamptz '2025-02-01 12:00:00+00',
      timestamptz '2025-02-01 12:00:00+00',
      null, 'adapter:1'
    )
  $$,
  $$ values ('inserted', 'obs-conflict-a') $$,
  'first vintage insert succeeds'
);

select results_eq(
  $$
    select status::text
    from research.try_insert_observation(
      'obs-conflict-b',
      '11111111-1111-4111-8111-111111111111',
      'bls.ln.LNS14000000', 'bls', 'bls_cps_unemployment_rate', 'bls_cps_unemployment_rate',
      date '2024-03-01', null, 'monthly', 'US', 'percent', 'seasonally_adjusted',
      '3.9', 'observed', 'latest_revised', date '2024-02-01',
      null, null, 'unknown',
      timestamptz '2025-02-01 12:00:00+00',
      timestamptz '2025-02-01 12:00:00+00',
      null, 'adapter:1'
    )
  $$,
  $$ values ('conflict') $$,
  'contradictory value records conflict not overwrite'
);

select results_eq(
  $$
    select raw_value from research.economic_observations where observation_id = 'obs-conflict-a'
  $$,
  $$ values ('3.7') $$,
  'original observation value preserved'
);

select ok(
  (select count(*)::int from research.observation_conflicts) = 1,
  'one conflict row stored'
);

select ok(
  (
    select count(*)::int
    from research.try_insert_observation(
      'obs-conflict-b2',
      '11111111-1111-4111-8111-111111111111',
      'bls.ln.LNS14000000', 'bls', 'bls_cps_unemployment_rate', 'bls_cps_unemployment_rate',
      date '2024-03-01', null, 'monthly', 'US', 'percent', 'seasonally_adjusted',
      '4.1', 'observed', 'latest_revised', date '2024-02-01',
      null, null, 'unknown',
      timestamptz '2025-02-01 12:00:00+00',
      timestamptz '2025-02-01 12:00:00+00',
      null, 'adapter:1'
    ) t
    where t.status = 'conflict'
  ) = 1,
  'conflict path visible in same transaction before commit'
);

-- ---------------------------------------------------------------------------
-- Multi-dataset research run integrity
-- ---------------------------------------------------------------------------

insert into research.research_runs (
  run_id, executed_at, execution_status, primary_dataset_id, source_id, rights_record_id,
  analysis_mode, analysis_type, decision_at, evaluation_period,
  method_id, method_version, implementation_hash, config_id, config_hash,
  input_snapshot_hash, analytical_payload_hash, data_sufficiency,
  statistical_interpretation, causal_hypothesis, investment_implication,
  reproduction, narrative
)
values (
  'run-m2-test',
  timestamptz '2025-02-01 12:01:00+00',
  'completed',
  'bls.ln.LNS14000000',
  'bls_cps_unemployment_rate',
  'bls_cps_unemployment_rate',
  'point_in_time',
  'SAHM_UNEMPLOYMENT_GAP',
  timestamptz '2025-02-01 12:00:00+00',
  date '2024-12-01',
  'SAHM_UNEMPLOYMENT_GAP',
  '1.0.1',
  'abc',
  'sahm_published_v1',
  'cfg',
  'snap',
  'payload',
  'sufficient',
  'interpretation',
  'hypothesis',
  'no_action',
  '{"method_id":"SAHM_UNEMPLOYMENT_GAP"}'::jsonb,
  'narrative'
);

insert into research.research_run_datasets (
  run_id, dataset_id, source_id, rights_record_id, input_snapshot_hash, is_primary
)
values
  ('run-m2-test', 'bls.ln.LNS14000000', 'bls_cps_unemployment_rate', 'bls_cps_unemployment_rate', 'snap', true),
  ('run-m2-test', 'other.dataset', 'other_source', 'other_source', 'snap2', false);

insert into research.research_run_observations (run_id, observation_id, dataset_id)
values ('run-m2-test', 'obs-conflict-a', 'bls.ln.LNS14000000');

select throws_ok(
  $$
    insert into research.research_run_observations (run_id, observation_id, dataset_id)
    values ('run-m2-test', 'obs-run-other-dataset', 'other.dataset')
  $$,
  '23503',
  null,
  'run observation dataset must exist on research_run_datasets'
);

-- ---------------------------------------------------------------------------
-- Secret protection on retrievals
-- ---------------------------------------------------------------------------

select throws_ok(
  $$
    insert into research.source_retrievals (
      retrieval_id, source_id, dataset_id, rights_record_id, provider_id,
      adapter_id, adapter_version, retrieved_at, collection_mode,
      rights_decision_snapshot
    ) values (
      '33333333-3333-4333-8333-333333333333',
      'bls_cps_unemployment_rate', 'bls.ln.LNS14000000', 'bls_cps_unemployment_rate', 'bls',
      'x', '1', timestamptz '2025-02-01 12:00:00+00', 'fixture',
      '{"api_key":"secret"}'::jsonb
    )
  $$,
  '23514',
  null,
  'forbidden keys rejected in rights_decision_snapshot'
);

-- ---------------------------------------------------------------------------
-- Role privileges (not RLS-only; run as database owner, not anon)
-- ---------------------------------------------------------------------------

select ok(
  not has_schema_privilege('authenticated', 'research', 'USAGE'),
  'authenticated cannot use research schema'
);

select ok(
  not has_schema_privilege('anon', 'research', 'USAGE'),
  'anon cannot use research schema'
);

select ok(
  not has_table_privilege('authenticated', 'research.source_retrievals', 'SELECT'),
  'authenticated cannot select source_retrievals'
);

select ok(
  not has_table_privilege('authenticated', 'research.economic_observations', 'SELECT'),
  'authenticated cannot select economic_observations'
);

select ok(
  not has_table_privilege('authenticated', 'research.observation_conflicts', 'SELECT'),
  'authenticated cannot select observation_conflicts'
);

select ok(
  not has_table_privilege('authenticated', 'research.research_runs', 'SELECT'),
  'authenticated cannot select research_runs'
);

select ok(
  not has_table_privilege('authenticated', 'research.research_run_datasets', 'SELECT'),
  'authenticated cannot select research_run_datasets'
);

select ok(
  not has_table_privilege('authenticated', 'research.research_run_observations', 'SELECT'),
  'authenticated cannot select research_run_observations'
);

select ok(
  not has_table_privilege('anon', 'research.economic_observations', 'INSERT'),
  'anon cannot insert economic_observations'
);

select ok(
  not has_table_privilege('service_role', 'research.economic_observations', 'SELECT'),
  'service_role is not granted research table access'
);

select ok(
  has_table_privilege('research_writer', 'research.economic_observations', 'INSERT'),
  'research_writer can insert observations'
);

select ok(
  not has_table_privilege('research_writer', 'research.economic_observations', 'UPDATE'),
  'research_writer cannot update observations'
);

select ok(
  not has_table_privilege('research_writer', 'research.economic_observations', 'DELETE'),
  'research_writer cannot delete observations'
);

select ok(
  not has_table_privilege('research_writer', 'research.economic_observations', 'TRUNCATE'),
  'research_writer cannot truncate observations'
);

select throws_ok(
  $$
    update research.economic_observations
    set raw_value = '9.9'
    where observation_id = 'obs-conflict-a'
  $$,
  'P0001',
  null,
  'update blocked by append-only trigger (superuser still hits trigger)'
);

select ok(
  not has_table_privilege('authenticated', 'research.economic_observations', 'TRUNCATE'),
  'authenticated lacks truncate on economic_observations'
);

select * from finish();
rollback;
