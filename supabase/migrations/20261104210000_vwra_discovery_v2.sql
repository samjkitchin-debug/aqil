-- Retrospective VWRA discovery registry.
-- Extends the local research schema. It does not edit LH-H-001 through LH-H-007
-- or EVT-DEF-001 or EVT-DEF-002.
-- Apply locally only. Do not apply this file to a hosted project.
-- Same hosted prohibition as 20261104120000_historical_state_atlas.sql.

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
    'no_incremental_information',
    'descriptive',
    'retrospective_exploratory',
    'insufficient_sample'
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
    'no_incremental_information',
    'descriptive',
    'retrospective_exploratory',
    'insufficient_sample'
  )
);

create table research.discovery_v2_specifications (
  specification_id text not null,
  version integer not null,
  specification jsonb not null,
  specification_hash text not null,
  frozen_at timestamptz not null,
  publication_allowed boolean not null default false,
  primary key (specification_id, version),
  constraint discovery_v2_specifications_version_positive check (version >= 1),
  constraint discovery_v2_specifications_hash check (specification_hash ~ '^[0-9a-f]{64}$'),
  constraint discovery_v2_specifications_unpublished check (publication_allowed = false)
);

comment on table research.discovery_v2_specifications is
  'Frozen VWRA discovery rules. publication_allowed stays false. Local only.';

create table research.discovery_v2_method_runs (
  specification_id text not null,
  specification_version integer not null,
  method_id text not null,
  method_version text not null,
  implementation_hash text not null,
  config_hash text not null,
  parameter_policy text not null,
  method_class text not null,
  reconstruction text,
  status text not null,
  reason text,
  point_count integer not null,
  numeric_count integer not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (specification_id, specification_version, method_id),
  foreign key (specification_id, specification_version)
    references research.discovery_v2_specifications (specification_id, version),
  constraint discovery_v2_method_runs_class check (
    method_class in ('methodology', 'indicator', 'diagnostic', 'unavailable')
  ),
  constraint discovery_v2_method_runs_reconstruction check (
    reconstruction is null
    or reconstruction in (
      'retrospective_reconstruction',
      'retrospective_latest_revised'
    )
  ),
  constraint discovery_v2_method_runs_status check (
    status in ('succeeded', 'failed', 'unavailable')
  ),
  constraint discovery_v2_method_runs_failure_reason check (
    status = 'succeeded' or reason is not null
  ),
  constraint discovery_v2_method_runs_success_has_number check (
    status <> 'succeeded' or numeric_count > 0
  ),
  constraint discovery_v2_method_runs_hash check (
    implementation_hash ~ '^[0-9a-f]{64}$' and config_hash ~ '^[0-9a-f]{64}$'
  ),
  constraint discovery_v2_method_runs_unpublished check (publication_allowed = false)
);

comment on table research.discovery_v2_method_runs is
  'One replay of a registered method. A failure stores its reason. publication_allowed stays false.';

create table research.discovery_v2_method_points (
  specification_id text not null,
  specification_version integer not null,
  method_id text not null,
  series_key text not null,
  period_start date not null,
  period_end date not null,
  value_text text,
  direction text,
  change_text text,
  state_label text,
  unit text not null,
  reconstruction text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (
    specification_id, specification_version, method_id, series_key, period_start
  ),
  foreign key (specification_id, specification_version, method_id)
    references research.discovery_v2_method_runs (
      specification_id, specification_version, method_id
    ),
  constraint discovery_v2_method_points_reconstruction check (
    reconstruction in (
      'retrospective_reconstruction',
      'retrospective_latest_revised'
    )
  ),
  constraint discovery_v2_method_points_direction check (
    direction is null or direction in ('up', 'down', 'flat')
  ),
  constraint discovery_v2_method_points_value_or_label check (
    value_text is not null or state_label is not null
  ),
  constraint discovery_v2_method_points_unpublished check (publication_allowed = false)
);

comment on table research.discovery_v2_method_points is
  'Numerical method output. It is retrospective and is not an investment signal.';

create table research.discovery_v2_anchor_features (
  anchor_id text not null references research.decision_anchors (anchor_id),
  feature_id text not null,
  anchor_session date not null,
  period_end date not null,
  value_text text,
  state_label text,
  unit text not null,
  source text not null,
  method_id text,
  reconstruction text not null,
  usable_as_decision_input boolean not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  primary key (anchor_id, feature_id),
  constraint discovery_v2_anchor_features_not_after check (period_end <= anchor_session),
  constraint discovery_v2_anchor_features_not_outcome check (feature_id !~ '^outcome_'),
  constraint discovery_v2_anchor_features_no_surprise check (feature_id !~ 'surprise'),
  constraint discovery_v2_anchor_features_source check (
    source in ('added_transform', 'reconstructed_method')
  ),
  constraint discovery_v2_anchor_features_method check (
    (source = 'reconstructed_method' and method_id is not null)
    or (source = 'added_transform' and method_id is null)
  ),
  constraint discovery_v2_anchor_features_reconstruction check (
    reconstruction in (
      'retrospective_reconstruction',
      'retrospective_latest_revised',
      'stored_sessions'
    )
  ),
  constraint discovery_v2_anchor_features_not_decision check (
    usable_as_decision_input = false
  ),
  constraint discovery_v2_anchor_features_value check (
    value_text is not null or state_label is not null
  ),
  constraint discovery_v2_anchor_features_unpublished check (publication_allowed = false)
);

comment on table research.discovery_v2_anchor_features is
  'Added transforms and joined method output. A later period cannot sit on an earlier anchor.';

create table research.discovery_v2_trials (
  trial_id text primary key,
  specification_id text not null,
  specification_version integer not null,
  specification_hash text not null,
  experiment_id text not null,
  symbol text not null,
  feature text not null,
  paired_feature text,
  statistic text not null,
  outcome text not null,
  sample_count integer not null,
  non_overlapping_count integer not null,
  result_text text,
  refusal_reason text,
  p_value_text text,
  finding_class text not null,
  bh_diagnostic boolean,
  detail text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  foreign key (specification_id, specification_version)
    references research.discovery_v2_specifications (specification_id, version),
  constraint discovery_v2_trials_symbol check (symbol = 'VWRA'),
  constraint discovery_v2_trials_hash check (specification_hash ~ '^[0-9a-f]{64}$'),
  constraint discovery_v2_trials_result_or_refusal check (
    (result_text is null) <> (refusal_reason is null)
  ),
  constraint discovery_v2_trials_finding check (
    finding_class in (
      'descriptive',
      'retrospective_exploratory',
      'inconclusive',
      'insufficient_sample',
      'rejected'
    )
  ),
  constraint discovery_v2_trials_not_promoted check (
    finding_class not in (
      'statistically_supported',
      'economically_useful',
      'forward_validated'
    )
  ),
  constraint discovery_v2_trials_bh_cannot_promote check (
    bh_diagnostic is null or finding_class = 'descriptive'
  ),
  constraint discovery_v2_trials_unpublished check (publication_allowed = false)
);

comment on table research.discovery_v2_trials is
  'Declared, executed, and refused VWRA comparisons. A BH flag cannot promote a row.';

create table research.discovery_v2_findings (
  finding_id text primary key,
  specification_id text not null,
  specification_version integer not null,
  hypothesis_id text not null,
  experiment_id text not null,
  finding_class text not null,
  point_in_time boolean not null default false,
  independently_validated boolean not null default false,
  executable_strategy boolean not null default false,
  statement text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  foreign key (specification_id, specification_version)
    references research.discovery_v2_specifications (specification_id, version),
  constraint discovery_v2_findings_class check (
    finding_class in (
      'descriptive',
      'retrospective_exploratory',
      'inconclusive',
      'insufficient_sample',
      'rejected'
    )
  ),
  constraint discovery_v2_findings_not_point_in_time check (point_in_time = false),
  constraint discovery_v2_findings_not_validated check (independently_validated = false),
  constraint discovery_v2_findings_not_a_strategy check (executable_strategy = false),
  constraint discovery_v2_findings_unpublished check (publication_allowed = false)
);

comment on table research.discovery_v2_findings is
  'Retrospective findings. Point-in-time eligibility and independent validation stay empty.';

create table research.discovery_v2_casebook (
  case_id text primary key,
  specification_id text not null,
  specification_version integer not null,
  symbol text not null,
  episode_group text not null,
  family text not null,
  event_id text,
  anchor_session date,
  window_steps integer,
  value_text text,
  sample_count integer,
  detail text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  foreign key (specification_id, specification_version)
    references research.discovery_v2_specifications (specification_id, version),
  constraint discovery_v2_casebook_symbol check (symbol = 'VWRA'),
  constraint discovery_v2_casebook_window check (
    window_steps is null or window_steps in (21, 63, 126, 252)
  ),
  constraint discovery_v2_casebook_unpublished check (publication_allowed = false)
);

comment on table research.discovery_v2_casebook is
  'VWRA episodes and matched month-end anchors. Controls are not chosen by later returns.';

create view research.vwra_discovery_states as
select
  a.anchor_id,
  a.session_date as anchor_session,
  s.feature_id,
  s.value_text,
  null::text as state_label,
  s.clock as reconstruction,
  s.usable_as_decision_input,
  'atlas'::text as source,
  null::text as method_id
from research.decision_anchors a
join research.state_observations s on s.anchor_id = a.anchor_id
where a.symbol = 'VWRA'
  and a.anchor_kind = 'listing_month_end'
  and a.session_date >= date '2019-07-25'
union all
select
  f.anchor_id,
  f.anchor_session,
  f.feature_id,
  f.value_text,
  f.state_label,
  f.reconstruction,
  f.usable_as_decision_input,
  f.source,
  f.method_id
from research.discovery_v2_anchor_features f;

comment on view research.vwra_discovery_states is
  'VWRA atlas states plus added transforms and reconstructed method output. Outcomes are not in this view.';

create or replace view research.long_horizon_progress as
select
  (select count(distinct hypothesis_id) from research.hypotheses) as registered_hypotheses,
  (select count(*) from research.hypotheses) as hypothesis_versions,
  (select count(distinct experiment_id) from research.experiment_specifications)
    as registered_experiments,
  (select count(*) from research.experiment_specifications) as experiment_versions,
  (select count(*) from research.experiment_specifications where category = 'A')
    as category_a_specifications,
  (select count(*) from research.experiment_specifications where category = 'B')
    as category_b_specifications,
  (select count(*) from research.experiment_specifications where category = 'C')
    as category_c_specifications,
  (select count(*) from research.experiment_executions where state = 'succeeded')
    as succeeded_executions,
  (select count(*) from research.experiment_executions where state = 'failed')
    as failed_executions,
  (select count(*) from research.experiment_executions where state = 'blocked')
    as blocked_executions,
  (select count(*) from research.evidence_records) as evidence_records,
  (select count(*) from research.scientific_claims) as claim_versions,
  (select count(*) from research.scientific_claims where status_at_claim = 'rejected')
    as claims_rejected_at_version,
  (select count(*) from research.scientific_claims where status_at_claim = 'inconclusive')
    as claims_inconclusive_at_version,
  (select count(*) from research.scientific_claims where status_at_claim = 'statistically_supported')
    as claims_statistically_supported,
  (select count(*) from research.scientific_claims where status_at_claim = 'economically_useful')
    as claims_economically_useful,
  (select count(*) from research.scientific_claims where status_at_claim = 'forward_validated')
    as claims_forward_validated,
  (
    select count(distinct original_id)
    from research.candidate_design_rows
    where row_kind = 'signal'
  ) as candidate_signal_ids,
  (
    select count(distinct original_id)
    from research.candidate_design_rows
    where row_kind = 'scenario'
  ) as candidate_scenario_ids,
  (
    select count(*)
    from research.candidate_design_rows
    where empirical_result
  ) as candidate_rows_marked_as_results,
  (
    select count(*)
    from research.research_family_gates
    where gate = 'blocked'
  ) as blocked_families,
  (
    select count(*)
    from research.research_family_gates
    where gate = 'design_only_not_executed'
  ) as design_only_families,
  (
    select count(*)
    from research.experiment_executions
    where publication_allowed
  ) as executions_published,
  (select count(*) from research.discovery_v2_trials) as registered_comparisons,
  (
    select count(*)
    from research.discovery_v2_trials
    where result_text is not null
  ) as executed_comparisons,
  (
    select count(*)
    from research.discovery_v2_trials
    where refusal_reason is not null
  ) as refused_comparisons,
  (select count(*) from research.discovery_v2_findings) as retrospective_results,
  (
    select count(*)
    from research.discovery_v2_findings
    where point_in_time
  ) as point_in_time_results,
  (
    select count(*)
    from research.experiment_executions
    where state = 'succeeded'
      and coalesce(configuration->>'portfolio_path', '') <> 'not_called'
      and coalesce(configuration->>'portfolio_simulator', '') <> 'not_called'
      and coalesce(configuration->>'portfolio_comparison', '') <> 'blocked'
      and coalesce(configuration->>'portfolio_simulation', '') <> 'not_called'
  ) as portfolio_simulations,
  (
    select count(*)
    from research.scientific_claims
    where status_at_claim in (
      'statistically_supported',
      'economically_useful',
      'forward_validated'
    )
  ) as scientifically_validated_findings;

comment on view research.long_horizon_progress is
  'Portfolio simulations are executions that called the simulator. Dossier and discovery executions are separate counts. There is no completion percentage.';

create trigger discovery_v2_specifications_deny_mutation
before update or delete on research.discovery_v2_specifications
for each row execute function research.deny_row_mutation();

create trigger discovery_v2_method_runs_deny_mutation
before update or delete on research.discovery_v2_method_runs
for each row execute function research.deny_row_mutation();

create trigger discovery_v2_method_points_deny_mutation
before update or delete on research.discovery_v2_method_points
for each row execute function research.deny_row_mutation();

create trigger discovery_v2_anchor_features_deny_mutation
before update or delete on research.discovery_v2_anchor_features
for each row execute function research.deny_row_mutation();

create trigger discovery_v2_trials_deny_mutation
before update or delete on research.discovery_v2_trials
for each row execute function research.deny_row_mutation();

create trigger discovery_v2_findings_deny_mutation
before update or delete on research.discovery_v2_findings
for each row execute function research.deny_row_mutation();

create trigger discovery_v2_casebook_deny_mutation
before update or delete on research.discovery_v2_casebook
for each row execute function research.deny_row_mutation();

revoke all on table research.discovery_v2_specifications from public, anon, authenticated, service_role;
revoke all on table research.discovery_v2_method_runs from public, anon, authenticated, service_role;
revoke all on table research.discovery_v2_method_points from public, anon, authenticated, service_role;
revoke all on table research.discovery_v2_anchor_features from public, anon, authenticated, service_role;
revoke all on table research.discovery_v2_trials from public, anon, authenticated, service_role;
revoke all on table research.discovery_v2_findings from public, anon, authenticated, service_role;
revoke all on table research.discovery_v2_casebook from public, anon, authenticated, service_role;
revoke all on table research.vwra_discovery_states from public, anon, authenticated, service_role;

grant select, insert on table research.discovery_v2_specifications to research_writer;
grant select, insert on table research.discovery_v2_method_runs to research_writer;
grant select, insert on table research.discovery_v2_method_points to research_writer;
grant select, insert on table research.discovery_v2_anchor_features to research_writer;
grant select, insert on table research.discovery_v2_trials to research_writer;
grant select, insert on table research.discovery_v2_findings to research_writer;
grant select, insert on table research.discovery_v2_casebook to research_writer;
grant select on table research.vwra_discovery_states to research_writer;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'research_reader') then
    execute 'grant select on table research.discovery_v2_specifications to research_reader';
    execute 'grant select on table research.discovery_v2_method_runs to research_reader';
    execute 'grant select on table research.discovery_v2_method_points to research_reader';
    execute 'grant select on table research.discovery_v2_anchor_features to research_reader';
    execute 'grant select on table research.discovery_v2_trials to research_reader';
    execute 'grant select on table research.discovery_v2_findings to research_reader';
    execute 'grant select on table research.discovery_v2_casebook to research_reader';
    execute 'grant select on table research.vwra_discovery_states to research_reader';
  end if;
end $$;
