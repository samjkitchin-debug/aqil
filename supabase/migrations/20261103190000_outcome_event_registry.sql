-- Outcome-first event registry.
-- Extends the local research schema. It does not replace hypotheses, the
-- coverage matrix, or research.research_runs. Apply locally only.
-- Do not apply this file to a hosted project.

create table research.event_definitions (
  definition_id text not null,
  version integer not null,
  specification jsonb not null,
  specification_hash text not null,
  frozen_at timestamptz not null,
  publication_allowed boolean not null default false,
  primary key (definition_id, version),
  constraint event_definitions_version_positive check (version >= 1),
  constraint event_definitions_hash check (specification_hash ~ '^[0-9a-f]{64}$'),
  constraint event_definitions_total_return_blocked check (
    coalesce(specification->>'total_return_events', '') = 'blocked'
  ),
  constraint event_definitions_unpublished check (publication_allowed = false)
);

comment on table research.event_definitions is
  'Versioned price-event rules. Total-return events stay blocked. A later version is a new row.';

create table research.market_events (
  event_id text primary key,
  definition_id text not null,
  definition_version integer not null,
  symbol text not null,
  listing_currency text not null,
  family text not null,
  horizon_label text not null,
  start_date date not null,
  end_date date not null,
  label_confirmed_on date,
  price_return text not null,
  session_steps integer not null,
  max_intervening_drawdown text not null,
  up_session_fraction text not null,
  label_uses_later_prices boolean not null,
  usable_as_investment_signal boolean not null,
  historically_observable_at_event_date boolean not null,
  price_series_sha256 text not null,
  detail text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  foreign key (definition_id, definition_version)
    references research.event_definitions (definition_id, version),
  constraint market_events_family check (
    family in (
      'sustained_advance',
      'persistent_bull',
      'early_bull',
      'drawdown_recovery',
      'early_recovery',
      'sideways_then_advance',
      'relative_outperformance',
      'leadership_transition',
      'failed_rally',
      'negative_market',
      'flat_market'
    )
  ),
  constraint market_events_currency check (listing_currency ~ '^[A-Z]{3}$'),
  constraint market_events_dates check (end_date >= start_date),
  constraint market_events_steps check (session_steps >= 0),
  constraint market_events_signal_false check (usable_as_investment_signal = false),
  constraint market_events_hash check (price_series_sha256 ~ '^[0-9a-f]{64}$'),
  constraint market_events_vwra_start check (
    symbol <> 'VWRA' or start_date >= date '2019-07-25'
  ),
  constraint market_events_unpublished check (publication_allowed = false)
);

comment on table research.market_events is
  'Descriptive price events. A label may use later closes. No row is an investment signal. Total return is not stored here.';

create table research.event_family_counts (
  definition_id text not null,
  definition_version integer not null,
  symbol text not null,
  family text not null,
  horizon_label text not null,
  status text not null,
  reason text not null,
  event_count integer not null,
  windows_examined integer not null,
  qualifier_window_count integer,
  censored_count integer not null,
  price_series_sha256 text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (definition_id, definition_version, symbol, family, horizon_label),
  foreign key (definition_id, definition_version)
    references research.event_definitions (definition_id, version),
  constraint event_family_counts_status check (status in ('catalogued', 'blocked')),
  constraint event_family_counts_blocked_empty check (
    status <> 'blocked' or event_count = 0
  ),
  constraint event_family_counts_nonnegative check (
    event_count >= 0
    and windows_examined >= 0
    and censored_count >= 0
    and (qualifier_window_count is null or qualifier_window_count >= 0)
  ),
  constraint event_family_counts_hash check (price_series_sha256 ~ '^[0-9a-f]{64}$'),
  constraint event_family_counts_unpublished check (publication_allowed = false)
);

comment on table research.event_family_counts is
  'Per listing and family counts, including blocked families with zero events.';

create table research.feature_availability_rows (
  definition_id text not null,
  definition_version integer not null,
  symbol text not null,
  feature_id text not null,
  lookback_label text not null,
  clock text not null,
  availability text not null,
  covered_event_count integer not null,
  catalogued_event_count integer not null,
  seasonal_adjustment text,
  detail text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (
    definition_id, definition_version, symbol, feature_id, lookback_label
  ),
  foreign key (definition_id, definition_version)
    references research.event_definitions (definition_id, version),
  constraint feature_availability_clock check (
    clock in ('stored_sessions', 'calendar_months', 'not_applicable')
  ),
  constraint feature_availability_class check (
    availability in (
      'observable_from_stored_closes',
      'exploratory_latest_revised',
      'blocked',
      'not_applicable'
    )
  ),
  constraint feature_availability_counts check (
    covered_event_count >= 0
    and catalogued_event_count >= 0
    and covered_event_count <= catalogued_event_count
  ),
  constraint feature_availability_seasonal check (
    seasonal_adjustment is null
    or seasonal_adjustment in (
      'seasonally_adjusted',
      'not_seasonally_adjusted',
      'unknown'
    )
  ),
  constraint feature_availability_unpublished check (publication_allowed = false)
);

comment on table research.feature_availability_rows is
  'Whether a feature can be read around catalogued events. Latest-revised coverage is exploratory and is not a signal.';

create table research.comparison_periods (
  period_id text primary key,
  experiment_id text not null,
  experiment_version integer not null,
  symbol text not null,
  decision_date date not null,
  condition_met boolean not null,
  outcome_advance boolean not null,
  forward_price_return text not null,
  selected_on_future_return boolean not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  foreign key (experiment_id, experiment_version)
    references research.experiment_specifications (experiment_id, version),
  constraint comparison_periods_unique_decision unique (
    experiment_id, experiment_version, symbol, decision_date
  ),
  constraint comparison_periods_not_selected_on_future check (
    selected_on_future_return = false
  ),
  constraint comparison_periods_vwra check (
    symbol <> 'VWRA' or decision_date >= date '2019-07-25'
  ),
  constraint comparison_periods_unpublished check (publication_allowed = false)
);

comment on table research.comparison_periods is
  'Eligible month-ends for one frozen intersection. Rows are not chosen by the later return.';

create index market_events_symbol_family_idx
  on research.market_events (symbol, family);

create trigger event_definitions_deny_mutation
before update or delete on research.event_definitions
for each row
execute function research.deny_row_mutation();

create trigger market_events_deny_mutation
before update or delete on research.market_events
for each row
execute function research.deny_row_mutation();

create trigger event_family_counts_deny_mutation
before update or delete on research.event_family_counts
for each row
execute function research.deny_row_mutation();

create trigger feature_availability_rows_deny_mutation
before update or delete on research.feature_availability_rows
for each row
execute function research.deny_row_mutation();

create trigger comparison_periods_deny_mutation
before update or delete on research.comparison_periods
for each row
execute function research.deny_row_mutation();

revoke all on table research.event_definitions from public, anon, authenticated, service_role;
revoke all on table research.market_events from public, anon, authenticated, service_role;
revoke all on table research.event_family_counts from public, anon, authenticated, service_role;
revoke all on table research.feature_availability_rows from public, anon, authenticated, service_role;
revoke all on table research.comparison_periods from public, anon, authenticated, service_role;

grant select, insert on table research.event_definitions to research_writer;
grant select, insert on table research.market_events to research_writer;
grant select, insert on table research.event_family_counts to research_writer;
grant select, insert on table research.feature_availability_rows to research_writer;
grant select, insert on table research.comparison_periods to research_writer;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'research_reader') then
    execute 'grant select on table research.event_definitions to research_reader';
    execute 'grant select on table research.market_events to research_reader';
    execute 'grant select on table research.event_family_counts to research_reader';
    execute 'grant select on table research.feature_availability_rows to research_reader';
    execute 'grant select on table research.comparison_periods to research_reader';
  end if;
end $$;
