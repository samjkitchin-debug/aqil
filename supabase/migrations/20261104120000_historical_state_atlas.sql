-- Historical state atlas.
-- Extends the local research schema. It does not replace the scientific
-- registry or EVT-DEF-001. Apply locally only.
-- Do not apply this file to a hosted project.

alter table research.scientific_claims drop constraint scientific_claims_status;
alter table research.scientific_claims add constraint scientific_claims_status check (
  status_at_claim in (
    'proposed',
    'exploratory',
    'retrospective_only',
    'insufficient_data',
    'statistically_supported',
    'economically_useful',
    'rejected',
    'inconclusive',
    'superseded',
    'forward_validated',
    'no_incremental_information'
  )
);

alter table research.scientific_claims drop constraint scientific_claims_category_c_not_promoted;
alter table research.scientific_claims add constraint scientific_claims_category_c_not_promoted check (
  eligibility_class <> 'category_c_price_only'
  or status_at_claim in (
    'proposed',
    'exploratory',
    'retrospective_only',
    'insufficient_data',
    'rejected',
    'inconclusive',
    'superseded',
    'no_incremental_information'
  )
);

alter table research.scientific_status_events drop constraint scientific_status_events_status;
alter table research.scientific_status_events add constraint scientific_status_events_status check (
  status in (
    'proposed',
    'exploratory',
    'retrospective_only',
    'insufficient_data',
    'statistically_supported',
    'economically_useful',
    'rejected',
    'inconclusive',
    'superseded',
    'forward_validated',
    'no_incremental_information'
  )
);

create table research.atlas_specifications (
  specification_id text not null,
  version integer not null,
  specification jsonb not null,
  specification_hash text not null,
  frozen_at timestamptz not null,
  publication_allowed boolean not null default false,
  primary key (specification_id, version),
  constraint atlas_specifications_version_positive check (version >= 1),
  constraint atlas_specifications_hash check (specification_hash ~ '^[0-9a-f]{64}$'),
  constraint atlas_specifications_unpublished check (publication_allowed = false)
);

comment on table research.atlas_specifications is
  'Frozen historical-state atlas. A later version is a new row. publication_allowed stays false.';

create table research.decision_anchors (
  anchor_id text primary key,
  specification_id text not null,
  specification_version integer not null,
  specification_hash text not null,
  symbol text not null,
  anchor_kind text not null,
  session_date date not null,
  lookback_sufficient boolean not null,
  listing_currency text,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  foreign key (specification_id, specification_version)
    references research.atlas_specifications (specification_id, version),
  constraint decision_anchors_kind check (
    anchor_kind in ('listing_month_end', 'bea_gdp_release')
  ),
  constraint decision_anchors_unique unique (
    specification_id, specification_version, symbol, anchor_kind, session_date
  ),
  constraint decision_anchors_hash check (specification_hash ~ '^[0-9a-f]{64}$'),
  constraint decision_anchors_currency check (
    listing_currency is null or listing_currency ~ '^[A-Z]{3}$'
  ),
  constraint decision_anchors_unpublished check (publication_allowed = false)
);

comment on table research.decision_anchors is
  'One listing month-end, or one real BEA release date. Insufficient lookback does not delete the row. No market-transition anchor is stored.';

create table research.scientific_inventory_rows (
  specification_id text not null,
  specification_version integer not null,
  row_kind text not null,
  row_key text not null,
  payload jsonb not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (specification_id, specification_version, row_kind, row_key),
  foreign key (specification_id, specification_version)
    references research.atlas_specifications (specification_id, version),
  constraint scientific_inventory_rows_kind check (
    row_kind in (
      'economic_series',
      'method',
      'listing',
      'unavailable_dimension'
    )
  ),
  constraint scientific_inventory_rows_unpublished check (publication_allowed = false)
);

comment on table research.scientific_inventory_rows is
  'Machine-readable inventory. It is a report of stored inputs, not a second source of observations.';

create table research.state_observations (
  state_id text primary key,
  anchor_id text not null references research.decision_anchors (anchor_id),
  feature_id text not null,
  feature_family text not null,
  availability text not null,
  clock text not null,
  usable_as_decision_input boolean not null,
  value_text text,
  detail text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  constraint state_observations_unique_feature unique (anchor_id, feature_id),
  constraint state_observations_family check (
    feature_family in ('market', 'economic_retrospective', 'point_in_time')
  ),
  constraint state_observations_not_an_outcome check (feature_id !~ '^outcome_'),
  constraint state_observations_no_surprise check (feature_id !~ 'surprise'),
  constraint state_observations_availability check (
    availability in (
      'observed',
      'insufficient_lookback',
      'insufficient_frequency',
      'insufficient_gap_not_filled',
      'insufficient_zero_base',
      'insufficient_zero_variance',
      'insufficient_no_trough_after_peak',
      'insufficient_peer_date',
      'insufficient_no_vintage',
      'blocked_no_foreign_exchange',
      'blocked_no_consensus',
      'not_applicable'
    )
  ),
  constraint state_observations_clock check (
    clock in (
      'stored_sessions',
      'retrospective_latest_revised_release_lag_unknown',
      'point_in_time_observation'
    )
  ),
  constraint state_observations_value_presence check (
    (availability = 'observed') = (value_text is not null)
  ),
  constraint state_observations_retrospective_not_usable check (
    clock <> 'retrospective_latest_revised_release_lag_unknown'
    or usable_as_decision_input = false
  ),
  constraint state_observations_point_in_time_subject check (
    clock <> 'point_in_time_observation'
    or feature_id like 'bea.vintage.real_gdp.pct_preceding:%'
  ),
  constraint state_observations_unpublished check (publication_allowed = false)
);

comment on table research.state_observations is
  'A raw state at an anchor. It has no forward-return column. Latest-revised rows are not decision inputs.';

create table research.outcome_measures (
  outcome_id text primary key,
  anchor_id text not null references research.decision_anchors (anchor_id),
  horizon_label text not null,
  session_steps integer not null,
  status text not null,
  value_text text,
  labelled_advance boolean,
  readable_as_state_input boolean not null,
  known_at_anchor boolean not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  constraint outcome_measures_unique_horizon unique (anchor_id, horizon_label),
  constraint outcome_measures_horizon check (
    (horizon_label = '1m' and session_steps = 21)
    or (horizon_label = '3m' and session_steps = 63)
    or (horizon_label = '6m' and session_steps = 126)
    or (horizon_label = '12m' and session_steps = 252)
    or (horizon_label = '24m' and session_steps = 504)
    or (horizon_label = '36m' and session_steps = 756)
  ),
  constraint outcome_measures_status check (status in ('observed', 'censored')),
  constraint outcome_measures_censored_empty check (
    (
      status = 'censored'
      and value_text is null
      and labelled_advance is null
    )
    or (status = 'observed' and value_text is not null)
  ),
  constraint outcome_measures_not_a_state_input check (
    readable_as_state_input = false and known_at_anchor = false
  ),
  constraint outcome_measures_unpublished check (publication_allowed = false)
);

comment on table research.outcome_measures is
  'Forward results at an anchor. A row cannot be marked readable as a state input. A missing session is censored.';

create table research.anchor_event_links (
  anchor_id text not null references research.decision_anchors (anchor_id),
  event_id text not null references research.market_events (event_id),
  relation text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (anchor_id, event_id, relation),
  constraint anchor_event_links_relation check (relation = 'preceding_state'),
  constraint anchor_event_links_unpublished check (publication_allowed = false)
);

comment on table research.anchor_event_links is
  'Link from a stored price event back to the latest month-end anchor on or before its start. Event rows are not rewritten.';

create table research.market_episodes (
  episode_id text primary key,
  specification_id text not null,
  specification_version integer not null,
  symbol text not null,
  start_date date not null,
  end_date date not null,
  event_count integer not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  foreign key (specification_id, specification_version)
    references research.atlas_specifications (specification_id, version),
  constraint market_episodes_dates check (end_date >= start_date),
  constraint market_episodes_count check (event_count >= 2 or event_count = 1),
  constraint market_episodes_unpublished check (publication_allowed = false)
);

comment on table research.market_episodes is
  'Overlapping stored events on one symbol. The event catalogue is not redefined.';

create table research.market_episode_events (
  episode_id text not null references research.market_episodes (episode_id),
  event_id text not null references research.market_events (event_id),
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (episode_id, event_id),
  constraint market_episode_events_unpublished check (publication_allowed = false)
);

create table research.atlas_coverage_counts (
  specification_id text not null,
  specification_version integer not null,
  metric text not null,
  metric_count integer not null,
  detail text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (specification_id, specification_version, metric),
  foreign key (specification_id, specification_version)
    references research.atlas_specifications (specification_id, version),
  constraint atlas_coverage_counts_nonnegative check (metric_count >= 0),
  constraint atlas_coverage_counts_unpublished check (publication_allowed = false)
);

comment on table research.atlas_coverage_counts is
  'Counts and the content checksum for one atlas version. The checksum is not a second copy of the rows.';

create table research.atlas_claim_anchors (
  anchor_id text not null references research.decision_anchors (anchor_id),
  claim_id text not null,
  claim_version integer not null,
  role text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (anchor_id, claim_id, claim_version, role),
  foreign key (claim_id, claim_version)
    references research.scientific_claims (claim_id, version),
  constraint atlas_claim_anchors_role check (
    role in ('sequence_decision', 'primary_control', 'eligible_month_end')
  ),
  constraint atlas_claim_anchors_unpublished check (publication_allowed = false)
);

comment on table research.atlas_claim_anchors is
  'Eligible month-ends that entered LH-H-004. The link does not copy an outcome into a state.';

create index state_observations_anchor_idx
  on research.state_observations (anchor_id);

create index outcome_measures_anchor_idx
  on research.outcome_measures (anchor_id);

create index anchor_event_links_event_idx
  on research.anchor_event_links (event_id);

create view research.anchor_research_matrix as
select
  anchor.anchor_id,
  anchor.specification_id,
  anchor.specification_version,
  anchor.specification_hash,
  anchor.symbol,
  anchor.anchor_kind,
  anchor.session_date,
  anchor.lookback_sufficient,
  anchor.publication_allowed,
  (
    select count(*)
    from research.state_observations state
    where state.anchor_id = anchor.anchor_id
  ) as state_count,
  (
    select count(*)
    from research.outcome_measures outcome
    where outcome.anchor_id = anchor.anchor_id
  ) as outcome_count
from research.decision_anchors anchor;

comment on view research.anchor_research_matrix is
  'Research matrix at anchor grain. State values and outcome values stay in their own tables.';

create view research.event_preceding_states as
select
  event.event_id,
  event.symbol,
  event.family,
  event.horizon_label,
  event.start_date,
  link.anchor_id,
  state.state_id,
  state.feature_id,
  state.availability,
  state.clock,
  state.usable_as_decision_input,
  state.value_text
from research.market_events event
join research.anchor_event_links link
  on link.event_id = event.event_id
 and link.relation = 'preceding_state'
join research.state_observations state
  on state.anchor_id = link.anchor_id;

comment on view research.event_preceding_states is
  'From a stored market event to states at the preceding month-end anchor.';

create view research.state_later_outcomes as
select
  state.state_id,
  state.anchor_id,
  state.feature_id,
  state.clock,
  state.usable_as_decision_input,
  outcome.outcome_id,
  outcome.horizon_label,
  outcome.status as outcome_status,
  outcome.value_text as outcome_value,
  outcome.readable_as_state_input,
  outcome.known_at_anchor,
  claim_link.claim_id,
  claim_link.role as claim_role,
  claim.status_at_claim
from research.state_observations state
join research.outcome_measures outcome
  on outcome.anchor_id = state.anchor_id
left join research.atlas_claim_anchors claim_link
  on claim_link.anchor_id = state.anchor_id
left join research.scientific_claims claim
  on claim.claim_id = claim_link.claim_id
 and claim.version = claim_link.claim_version;

comment on view research.state_later_outcomes is
  'From a state identity to later outcomes on the same anchor, and to a claim when that anchor was scored.';

create trigger atlas_specifications_deny_mutation
before update or delete on research.atlas_specifications
for each row execute function research.deny_row_mutation();

create trigger decision_anchors_deny_mutation
before update or delete on research.decision_anchors
for each row execute function research.deny_row_mutation();

create trigger scientific_inventory_rows_deny_mutation
before update or delete on research.scientific_inventory_rows
for each row execute function research.deny_row_mutation();

create trigger state_observations_deny_mutation
before update or delete on research.state_observations
for each row execute function research.deny_row_mutation();

create trigger outcome_measures_deny_mutation
before update or delete on research.outcome_measures
for each row execute function research.deny_row_mutation();

create trigger anchor_event_links_deny_mutation
before update or delete on research.anchor_event_links
for each row execute function research.deny_row_mutation();

create trigger market_episodes_deny_mutation
before update or delete on research.market_episodes
for each row execute function research.deny_row_mutation();

create trigger market_episode_events_deny_mutation
before update or delete on research.market_episode_events
for each row execute function research.deny_row_mutation();

create trigger atlas_coverage_counts_deny_mutation
before update or delete on research.atlas_coverage_counts
for each row execute function research.deny_row_mutation();

create trigger atlas_claim_anchors_deny_mutation
before update or delete on research.atlas_claim_anchors
for each row execute function research.deny_row_mutation();

revoke all on table research.atlas_specifications from public, anon, authenticated, service_role;
revoke all on table research.decision_anchors from public, anon, authenticated, service_role;
revoke all on table research.scientific_inventory_rows from public, anon, authenticated, service_role;
revoke all on table research.state_observations from public, anon, authenticated, service_role;
revoke all on table research.outcome_measures from public, anon, authenticated, service_role;
revoke all on table research.anchor_event_links from public, anon, authenticated, service_role;
revoke all on table research.market_episodes from public, anon, authenticated, service_role;
revoke all on table research.market_episode_events from public, anon, authenticated, service_role;
revoke all on table research.atlas_coverage_counts from public, anon, authenticated, service_role;
revoke all on table research.atlas_claim_anchors from public, anon, authenticated, service_role;

revoke all on table research.anchor_research_matrix from public, anon, authenticated, service_role;
revoke all on table research.event_preceding_states from public, anon, authenticated, service_role;
revoke all on table research.state_later_outcomes from public, anon, authenticated, service_role;

grant select, insert on table research.atlas_specifications to research_writer;
grant select, insert on table research.decision_anchors to research_writer;
grant select, insert on table research.scientific_inventory_rows to research_writer;
grant select, insert on table research.state_observations to research_writer;
grant select, insert on table research.outcome_measures to research_writer;
grant select, insert on table research.anchor_event_links to research_writer;
grant select, insert on table research.market_episodes to research_writer;
grant select, insert on table research.market_episode_events to research_writer;
grant select, insert on table research.atlas_coverage_counts to research_writer;
grant select, insert on table research.atlas_claim_anchors to research_writer;

grant select on table research.anchor_research_matrix to research_writer;
grant select on table research.event_preceding_states to research_writer;
grant select on table research.state_later_outcomes to research_writer;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'research_reader') then
    execute 'grant select on table research.atlas_specifications to research_reader';
    execute 'grant select on table research.decision_anchors to research_reader';
    execute 'grant select on table research.scientific_inventory_rows to research_reader';
    execute 'grant select on table research.state_observations to research_reader';
    execute 'grant select on table research.outcome_measures to research_reader';
    execute 'grant select on table research.anchor_event_links to research_reader';
    execute 'grant select on table research.market_episodes to research_reader';
    execute 'grant select on table research.market_episode_events to research_reader';
    execute 'grant select on table research.atlas_coverage_counts to research_reader';
    execute 'grant select on table research.atlas_claim_anchors to research_reader';
    execute 'grant select on table research.anchor_research_matrix to research_reader';
    execute 'grant select on table research.event_preceding_states to research_reader';
    execute 'grant select on table research.state_later_outcomes to research_reader';
  end if;
end $$;
