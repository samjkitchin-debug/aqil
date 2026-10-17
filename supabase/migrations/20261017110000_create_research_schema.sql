-- M2 Phase 1: durable research history (append-only, not exposed via Data API).
-- Transaction note: use research.try_insert_observation() so conflicts are recorded in the
-- same transaction as the append attempt without UPDATE on existing rows. Commit to persist
-- both a new row and a conflict record; ROLLBACK drops uncommitted work (caller may commit
-- conflicts in a separate transaction before rolling back a larger batch if needed).

create schema research;

comment on schema research is
  'Private research persistence. Not listed in supabase/config.toml [api].schemas.';

-- ---------------------------------------------------------------------------
-- Roles (least privilege; no secrets in Git)
-- ---------------------------------------------------------------------------

create role research_writer nologin;
comment on role research_writer is
  'Append-only research DML. Grant to a separately provisioned worker login role at deploy time; not granted to anon/authenticated.';

create role research_worker_app nologin;
comment on role research_worker_app is
  'Placeholder for the future LOGIN worker principal. Credentials via Supabase vault or host secret store only; enable LOGIN in a deploy-specific migration after approval.';

grant research_writer to research_worker_app;

revoke all on schema research from public;
revoke all on schema research from anon;
revoke all on schema research from authenticated;

grant usage on schema research to research_writer;

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------

create or replace function research.compute_model_available_at(
  p_series_provenance text,
  p_availability_precision text,
  p_provider_vintage_date date,
  p_earliest_model_available_at timestamptz,
  p_source_release_at timestamptz
)
returns timestamptz
language sql
immutable
set search_path = research, pg_temp
as $$
  select case
    when p_series_provenance = 'latest_revised' then null::timestamptz
    when p_earliest_model_available_at is not null then p_earliest_model_available_at
    when p_availability_precision = 'date' then
      ((p_provider_vintage_date + 1)::timestamp at time zone 'UTC')
    else null::timestamptz
  end;
$$;

comment on function research.compute_model_available_at is
  'Conservative UTC availability: date-only precision uses start of day after provider_vintage_date.';

create or replace function research.release_identity_key(
  p_source_release_at timestamptz,
  p_retrieved_at timestamptz
)
returns text
language sql
immutable
set search_path = research, pg_temp
as $$
  select coalesce(p_source_release_at::text, p_retrieved_at::text);
$$;

create or replace function research.jsonb_forbidden_secret_keys()
returns text[]
language sql
immutable
set search_path = research, pg_temp
as $$
  select array[
    'api_key',
    'apikey',
    'registrationkey',
    'authorization',
    'password',
    'secret',
    'token',
    'bearer',
    'credential'
  ]::text[];
$$;

create or replace function research.text_contains_secret_pattern(p_value text)
returns boolean
language sql
immutable
set search_path = research, pg_temp
as $$
  select p_value is not null
    and (
      p_value ~* '(api[_-]?key|registrationkey|authorization:|bearer\s|password\s*=)'
      or p_value ~* '://[^/@]+:[^/@]+@'
    );
$$;

create or replace function research.jsonb_has_forbidden_keys(p_obj jsonb)
returns boolean
language plpgsql
immutable
set search_path = research, pg_temp
as $$
declare
  forbidden text[] := research.jsonb_forbidden_secret_keys();
  k text;
begin
  if p_obj is null then
    return false;
  end if;
  foreach k in array forbidden loop
    if p_obj ? k then
      return true;
    end if;
  end loop;
  return false;
end;
$$;

create or replace function research.deny_row_mutation()
returns trigger
language plpgsql
set search_path = research, pg_temp
as $$
begin
  raise exception 'research.% is append-only; % is not permitted', tg_table_name, tg_op;
end;
$$;

-- ---------------------------------------------------------------------------
-- source_retrievals
-- ---------------------------------------------------------------------------

create table research.source_retrievals (
  retrieval_id uuid primary key default gen_random_uuid(),
  source_id text not null,
  dataset_id text not null,
  rights_record_id text not null,
  provider_id text not null,
  adapter_id text not null,
  adapter_version text not null,
  retrieved_at timestamptz not null,
  collection_mode text not null,
  endpoint_host text,
  request_series_ids text[] not null default '{}',
  request_year_start integer,
  request_year_end integer,
  attempt_count integer not null default 1,
  http_status integer,
  provider_status text,
  response_byte_count integer,
  rights_decision_snapshot jsonb not null default '{}'::jsonb,
  ingest_notes text[] not null default '{}',
  recorded_at timestamptz not null default now(),
  constraint source_retrievals_collection_mode check (
    collection_mode in ('live', 'fixture', 'replay')
  ),
  constraint source_retrievals_attempt_positive check (attempt_count >= 1),
  constraint source_retrievals_year_range check (
    request_year_start is null
    or request_year_end is null
    or request_year_end >= request_year_start
  ),
  constraint source_retrievals_no_secret_endpoint check (
    endpoint_host is null
    or (
      endpoint_host !~ '[?#]'
      and not research.text_contains_secret_pattern(endpoint_host)
    )
  ),
  constraint source_retrievals_rights_snapshot_keys check (
    not research.jsonb_has_forbidden_keys(rights_decision_snapshot)
  )
);

comment on table research.source_retrievals is
  'Immutable provider fetch metadata. No credentials in URLs or JSON snapshots.';

create trigger source_retrievals_deny_mutation
before update or delete on research.source_retrievals
for each row
execute function research.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- economic_observations
-- ---------------------------------------------------------------------------

create table research.economic_observations (
  observation_id text primary key,
  retrieval_id uuid not null references research.source_retrievals (retrieval_id),
  schema_version text not null default '1.0',
  dataset_id text not null,
  provider_id text not null,
  source_id text not null,
  rights_record_id text not null,
  period_start date not null,
  period_end date,
  frequency text not null,
  geography text not null,
  unit text not null,
  seasonal_adjustment text not null,
  raw_value text not null,
  quality_status text not null,
  series_provenance text not null,
  provider_vintage_date date not null,
  source_release_at timestamptz,
  earliest_model_available_at timestamptz,
  availability_precision text not null,
  retrieved_at timestamptz not null,
  first_seen_at timestamptz not null,
  source_locator text,
  adapter_version text not null,
  supersedes_observation_id text references research.economic_observations (observation_id),
  release_identity_key text not null,
  recorded_at timestamptz not null default now(),
  constraint economic_observations_schema_version check (schema_version = '1.0'),
  constraint economic_observations_frequency check (
    frequency in ('daily', 'weekly', 'monthly', 'quarterly', 'annual')
  ),
  constraint economic_observations_seasonal_adjustment check (
    seasonal_adjustment in ('seasonally_adjusted', 'not_seasonally_adjusted', 'unknown')
  ),
  constraint economic_observations_quality_status check (
    quality_status in ('observed', 'missing', 'contested', 'retracted')
  ),
  constraint economic_observations_series_provenance check (
    series_provenance in ('provider_vintage', 'latest_revised', 'aqil_archived')
  ),
  constraint economic_observations_availability_precision check (
    availability_precision in ('timestamp', 'date', 'unknown')
  ),
  constraint economic_observations_period_order check (
    period_end is null or period_end >= period_start
  ),
  constraint economic_observations_first_seen_order check (first_seen_at <= retrieved_at),
  constraint economic_observations_source_release_order check (
    source_release_at is null or source_release_at <= retrieved_at
  ),
  constraint economic_observations_earliest_after_release check (
    earliest_model_available_at is null
    or source_release_at is null
    or earliest_model_available_at >= source_release_at
  ),
  constraint economic_observations_temporal_integrity check (
    source_release_at is null
    or research.compute_model_available_at(
      series_provenance,
      availability_precision,
      provider_vintage_date,
      earliest_model_available_at,
      source_release_at
    ) is null
    or research.compute_model_available_at(
      series_provenance,
      availability_precision,
      provider_vintage_date,
      earliest_model_available_at,
      source_release_at
    ) >= source_release_at
  ),
  constraint economic_observations_latest_revised_precision check (
    series_provenance <> 'latest_revised'
    or (
      availability_precision = 'unknown'
      and earliest_model_available_at is null
    )
  ),
  constraint economic_observations_provider_vintage_precision check (
    series_provenance <> 'provider_vintage'
    or availability_precision in ('date', 'timestamp')
  ),
  constraint economic_observations_provider_vintage_availability check (
    series_provenance <> 'provider_vintage'
    or availability_precision = 'date'
    or earliest_model_available_at is not null
  ),
  constraint economic_observations_aqil_archived_availability check (
    series_provenance <> 'aqil_archived'
    or earliest_model_available_at is not null
  ),
  constraint economic_observations_raw_value_observed check (
    quality_status <> 'observed'
    or raw_value ~ '^-?\d+(\.\d+)?$'
  ),
  constraint economic_observations_raw_value_missing check (
    quality_status <> 'missing'
    or raw_value ~ '^-?\d+(\.\d+)?$'
  ),
  constraint economic_observations_release_key check (
    release_identity_key = research.release_identity_key(source_release_at, retrieved_at)
  )
);

create unique index economic_observations_vintage_identity_idx
on research.economic_observations (
  dataset_id,
  period_start,
  provider_vintage_date,
  release_identity_key
);

create index economic_observations_retrieval_id_idx
on research.economic_observations (retrieval_id);

create or replace function research.enforce_observation_retrieval_consistency()
returns trigger
language plpgsql
set search_path = research, pg_temp
as $$
declare
  r research.source_retrievals;
begin
  select * into r from research.source_retrievals where retrieval_id = new.retrieval_id;
  if not found then
    raise exception 'unknown retrieval_id %', new.retrieval_id;
  end if;
  if new.source_id <> r.source_id
    or new.dataset_id <> r.dataset_id
    or new.rights_record_id <> r.rights_record_id then
    raise exception
      'observation source/dataset/rights must match source_retrievals row';
  end if;
  return new;
end;
$$;

create trigger economic_observations_retrieval_consistency
before insert on research.economic_observations
for each row
execute function research.enforce_observation_retrieval_consistency();

create trigger economic_observations_deny_mutation
before update or delete on research.economic_observations
for each row
execute function research.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- observation_conflicts
-- ---------------------------------------------------------------------------

create table research.observation_conflicts (
  conflict_id uuid primary key default gen_random_uuid(),
  retrieval_id uuid not null references research.source_retrievals (retrieval_id),
  existing_observation_id text not null references research.economic_observations (observation_id),
  rejected_observation_id text not null,
  rejected_raw_value text not null,
  conflict_kind text not null default 'value_mismatch',
  detail text not null,
  recorded_at timestamptz not null default now(),
  constraint observation_conflicts_kind check (
    conflict_kind in ('value_mismatch', 'identity_collision')
  )
);

create index observation_conflicts_existing_idx
on research.observation_conflicts (existing_observation_id);

create trigger observation_conflicts_deny_mutation
before update or delete on research.observation_conflicts
for each row
execute function research.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- research_runs (immutable analytical record)
-- ---------------------------------------------------------------------------

create table research.research_runs (
  run_id text primary key,
  executed_at timestamptz not null,
  execution_status text not null,
  primary_dataset_id text not null,
  source_id text not null,
  rights_record_id text not null,
  analysis_mode text not null,
  analysis_type text not null,
  decision_at timestamptz not null,
  evaluation_period date not null,
  method_id text not null,
  method_version text not null,
  implementation_hash text not null,
  config_id text not null,
  config_hash text not null,
  input_snapshot_hash text not null,
  analytical_payload_hash text not null default '',
  data_sufficiency text not null,
  missing_data_reason text,
  calculation jsonb,
  statistical_interpretation text not null,
  causal_hypothesis text not null,
  market_pricing text not null default 'unknown',
  investment_implication text not null,
  assumptions jsonb not null default '[]'::jsonb,
  limitations jsonb not null default '[]'::jsonb,
  observation_ids jsonb not null default '[]'::jsonb,
  adapter_ids jsonb not null default '[]'::jsonb,
  ingest_notes jsonb not null default '[]'::jsonb,
  reproduction jsonb not null,
  narrative text not null,
  publication_allowed boolean not null default false,
  verification_status text not null default 'unverified',
  evidence_reasons jsonb not null default '[]'::jsonb,
  recorded_at timestamptz not null default now(),
  constraint research_runs_execution_status check (
    execution_status in (
      'completed',
      'completed_insufficient',
      'failed_rights',
      'failed_ingest',
      'failed_method'
    )
  ),
  constraint research_runs_analysis_mode check (
    analysis_mode in ('point_in_time', 'latest_revised')
  ),
  constraint research_runs_data_sufficiency check (
    data_sufficiency in ('sufficient', 'insufficient')
  ),
  constraint research_runs_investment_implication check (
    investment_implication in ('no_action', 'insufficient_evidence')
  )
);

create trigger research_runs_deny_mutation
before update or delete on research.research_runs
for each row
execute function research.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- research_run_datasets (multi-dataset rights + snapshot per run)
-- ---------------------------------------------------------------------------

create table research.research_run_datasets (
  run_id text not null references research.research_runs (run_id),
  dataset_id text not null,
  source_id text not null,
  rights_record_id text not null,
  input_snapshot_hash text not null,
  is_primary boolean not null default false,
  recorded_at timestamptz not null default now(),
  primary key (run_id, dataset_id)
);

create trigger research_run_datasets_deny_mutation
before update or delete on research.research_run_datasets
for each row
execute function research.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- research_run_observations (evidence links)
-- ---------------------------------------------------------------------------

create table research.research_run_observations (
  run_id text not null references research.research_runs (run_id),
  observation_id text not null references research.economic_observations (observation_id),
  dataset_id text not null,
  recorded_at timestamptz not null default now(),
  primary key (run_id, observation_id),
  foreign key (run_id, dataset_id)
    references research.research_run_datasets (run_id, dataset_id)
);

create index research_run_observations_dataset_idx
on research.research_run_observations (run_id, dataset_id);

create trigger research_run_observations_deny_mutation
before update or delete on research.research_run_observations
for each row
execute function research.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- Append API (conflict-safe, no UPDATE on existing observations)
-- ---------------------------------------------------------------------------

create type research.append_status as enum ('inserted', 'unchanged', 'conflict');

create or replace function research.try_insert_observation(
  p_observation_id text,
  p_retrieval_id uuid,
  p_dataset_id text,
  p_provider_id text,
  p_source_id text,
  p_rights_record_id text,
  p_period_start date,
  p_period_end date,
  p_frequency text,
  p_geography text,
  p_unit text,
  p_seasonal_adjustment text,
  p_raw_value text,
  p_quality_status text,
  p_series_provenance text,
  p_provider_vintage_date date,
  p_source_release_at timestamptz,
  p_earliest_model_available_at timestamptz,
  p_availability_precision text,
  p_retrieved_at timestamptz,
  p_first_seen_at timestamptz,
  p_source_locator text,
  p_adapter_version text,
  p_supersedes_observation_id text default null
)
returns table (
  status research.append_status,
  observation_id text,
  conflict_id uuid
)
language plpgsql
set search_path = research, pg_temp
as $$
declare
  v_release_key text;
  v_existing research.economic_observations;
  v_conflict_id uuid;
begin
  v_release_key := research.release_identity_key(p_source_release_at, p_retrieved_at);

  select *
  into v_existing
  from research.economic_observations eo
  where eo.dataset_id = p_dataset_id
    and eo.period_start = p_period_start
    and eo.provider_vintage_date = p_provider_vintage_date
    and eo.release_identity_key = v_release_key;

  if not found then
    insert into research.economic_observations (
      observation_id,
      retrieval_id,
      dataset_id,
      provider_id,
      source_id,
      rights_record_id,
      period_start,
      period_end,
      frequency,
      geography,
      unit,
      seasonal_adjustment,
      raw_value,
      quality_status,
      series_provenance,
      provider_vintage_date,
      source_release_at,
      earliest_model_available_at,
      availability_precision,
      retrieved_at,
      first_seen_at,
      source_locator,
      adapter_version,
      supersedes_observation_id,
      release_identity_key
    )
    values (
      p_observation_id,
      p_retrieval_id,
      p_dataset_id,
      p_provider_id,
      p_source_id,
      p_rights_record_id,
      p_period_start,
      p_period_end,
      p_frequency,
      p_geography,
      p_unit,
      p_seasonal_adjustment,
      p_raw_value,
      p_quality_status,
      p_series_provenance,
      p_provider_vintage_date,
      p_source_release_at,
      p_earliest_model_available_at,
      p_availability_precision,
      p_retrieved_at,
      p_first_seen_at,
      p_source_locator,
      p_adapter_version,
      p_supersedes_observation_id,
      v_release_key
    );
    return query select 'inserted'::research.append_status, p_observation_id, null::uuid;
    return;
  end if;

  if v_existing.raw_value = p_raw_value then
    return query select 'unchanged'::research.append_status, v_existing.observation_id, null::uuid;
    return;
  end if;

  insert into research.observation_conflicts (
    retrieval_id,
    existing_observation_id,
    rejected_observation_id,
    rejected_raw_value,
    detail
  )
  values (
    p_retrieval_id,
    v_existing.observation_id,
    p_observation_id,
    p_raw_value,
    format(
      'vintage identity collision: existing value %s, rejected %s',
      v_existing.raw_value,
      p_raw_value
    )
  )
  returning observation_conflicts.conflict_id into v_conflict_id;

  return query select 'conflict'::research.append_status, v_existing.observation_id, v_conflict_id;
end;
$$;

-- ---------------------------------------------------------------------------
-- Privileges (grants-only isolation; RLS not enabled on research schema)
-- ---------------------------------------------------------------------------

grant select, insert on all tables in schema research to research_writer;
grant usage, select on all sequences in schema research to research_writer;

alter default privileges in schema research
revoke all on tables from public;

alter default privileges in schema research
grant select, insert on tables to research_writer;

revoke all on all tables in schema research from public;
revoke all on all tables in schema research from anon;
revoke all on all tables in schema research from authenticated;
revoke all on all tables in schema research from service_role;

revoke all on all sequences in schema research from public;
revoke all on all sequences in schema research from anon;
revoke all on all sequences in schema research from authenticated;
revoke all on all sequences in schema research from service_role;

revoke all on all functions in schema research from public;
revoke all on all functions in schema research from anon;
revoke all on all functions in schema research from authenticated;
revoke all on all functions in schema research from service_role;

grant execute on function research.try_insert_observation(
  text,
  uuid,
  text,
  text,
  text,
  text,
  date,
  date,
  text,
  text,
  text,
  text,
  text,
  text,
  text,
  date,
  timestamptz,
  timestamptz,
  text,
  timestamptz,
  timestamptz,
  text,
  text,
  text
) to research_writer;

-- Migration owner only (local CI / hosted apply role). Not granted to anon, authenticated or service_role.
grant research_writer to postgres;
