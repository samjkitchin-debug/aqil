-- M4: forward intelligence (ETF exposure, catalysts, scenarios, outcomes).
-- Private schema — not exposed via Supabase Data API.

create schema forward;

comment on schema forward is
  'Forward intelligence persistence (ETF holdings, catalysts, scenarios). Not in [api].schemas.';

revoke all on schema forward from public;
revoke all on schema forward from anon;
revoke all on schema forward from authenticated;

grant usage on schema forward to research_writer;

-- ---------------------------------------------------------------------------
-- ETF identity (versioned append-only records)
-- ---------------------------------------------------------------------------

create table forward.etf_instrument_records (
  record_id uuid primary key default gen_random_uuid(),
  etf_id text not null,
  schema_version text not null default '1.0',
  payload jsonb not null,
  source_id text not null,
  source_locator text,
  verification_date date not null,
  research_status text not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint etf_instrument_payload_object check (jsonb_typeof(payload) = 'object')
);

create index etf_instrument_records_etf_id_idx
  on forward.etf_instrument_records (etf_id, recorded_at desc);

-- ---------------------------------------------------------------------------
-- Holdings snapshots (dated, not silently renormalised)
-- ---------------------------------------------------------------------------

create table forward.etf_holdings_snapshots (
  snapshot_id uuid primary key default gen_random_uuid(),
  etf_id text not null,
  as_of_date date not null,
  source_publication_date date,
  retrieved_at timestamptz not null,
  completeness text not null,
  source_id text not null,
  source_locator text,
  licence_evidence text,
  currency text,
  payload jsonb not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint holdings_payload_object check (jsonb_typeof(payload) = 'object')
);

create unique index etf_holdings_snapshots_identity_idx
  on forward.etf_holdings_snapshots (etf_id, as_of_date, source_id, retrieved_at);

create table forward.etf_holding_lines (
  snapshot_id uuid not null references forward.etf_holdings_snapshots (snapshot_id) on delete restrict,
  line_id text not null,
  holding_name text not null,
  issuer_id text,
  weight_percentage numeric(8, 4) not null,
  weight_is_estimated boolean not null default false,
  line_currency text,
  category text not null default 'equity',
  primary key (snapshot_id, line_id),
  constraint weight_non_negative check (weight_percentage >= 0)
);

-- ---------------------------------------------------------------------------
-- Catalyst registry
-- ---------------------------------------------------------------------------

create table forward.catalyst_events (
  event_id text primary key,
  schema_version text not null default '1.0',
  category text not null,
  subject_type text not null,
  subject_id text not null,
  title text not null,
  scheduled_at timestamptz,
  timezone text,
  date_precision text not null,
  status text not null,
  source_id text not null,
  source_locator text,
  provider_published_at timestamptz,
  first_observed_at timestamptz not null,
  last_verified_at timestamptz not null,
  payload jsonb not null default '{}'::jsonb,
  recorded_at timestamptz not null default (timezone('utc', now()))
);

create table forward.catalyst_event_revisions (
  revision_id uuid primary key default gen_random_uuid(),
  event_id text not null references forward.catalyst_events (event_id) on delete restrict,
  previous_scheduled_at timestamptz,
  new_scheduled_at timestamptz,
  observed_at timestamptz not null,
  reason text not null,
  source_id text not null
);

-- ---------------------------------------------------------------------------
-- Exposure links and materiality
-- ---------------------------------------------------------------------------

create table forward.catalyst_etf_exposure (
  exposure_id uuid primary key default gen_random_uuid(),
  event_id text not null references forward.catalyst_events (event_id) on delete restrict,
  etf_id text not null,
  snapshot_id uuid not null references forward.etf_holdings_snapshots (snapshot_id) on delete restrict,
  issuer_id text not null,
  weight_percentage numeric(8, 4) not null,
  materiality text not null,
  materiality_rules_version text not null,
  rationale text not null,
  holdings_completeness text not null,
  snapshot_as_of date not null,
  recorded_at timestamptz not null default (timezone('utc', now()))
);

create index catalyst_etf_exposure_event_idx on forward.catalyst_etf_exposure (event_id);

-- ---------------------------------------------------------------------------
-- Expectations and immutable pre-event scenarios
-- ---------------------------------------------------------------------------

create table forward.event_expectations (
  expectation_id uuid primary key default gen_random_uuid(),
  event_id text not null references forward.catalyst_events (event_id) on delete restrict,
  recorded_at timestamptz not null,
  payload jsonb not null,
  source_id text not null,
  constraint expectation_payload_object check (jsonb_typeof(payload) = 'object')
);

create table forward.forward_scenarios (
  scenario_id uuid primary key,
  event_id text not null references forward.catalyst_events (event_id) on delete restrict,
  frozen_at timestamptz not null,
  payload jsonb not null,
  payload_hash text not null,
  constraint scenario_payload_object check (jsonb_typeof(payload) = 'object')
);

create or replace function forward.deny_forward_scenario_mutation()
returns trigger
language plpgsql
set search_path = forward, pg_temp
as $$
begin
  raise exception 'forward_scenarios are immutable after freeze';
end;
$$;

create trigger forward_scenarios_immutable
  before update or delete on forward.forward_scenarios
  for each row
  execute function forward.deny_forward_scenario_mutation();

-- ---------------------------------------------------------------------------
-- Post-event outcomes (append-only)
-- ---------------------------------------------------------------------------

create table forward.event_outcomes (
  outcome_id uuid primary key default gen_random_uuid(),
  event_id text not null references forward.catalyst_events (event_id) on delete restrict,
  scenario_id uuid references forward.forward_scenarios (scenario_id) on delete restrict,
  observed_at timestamptz not null,
  payload jsonb not null,
  source_id text not null,
  constraint outcome_payload_object check (jsonb_typeof(payload) = 'object')
);

-- ---------------------------------------------------------------------------
-- Privileges
-- ---------------------------------------------------------------------------

grant select, insert on all tables in schema forward to research_writer;
grant usage, select on all sequences in schema forward to research_writer;

alter default privileges in schema forward
  revoke all on tables from public;

alter default privileges in schema forward
  grant select, insert on tables to research_writer;

revoke all on all tables in schema forward from public;
revoke all on all tables in schema forward from anon;
revoke all on all tables in schema forward from authenticated;
revoke all on all tables in schema forward from service_role;

grant execute on all functions in schema forward to research_writer;

alter default privileges in schema forward
  grant execute on functions to research_writer;
