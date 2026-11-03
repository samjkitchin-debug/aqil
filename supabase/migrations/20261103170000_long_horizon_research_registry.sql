-- Long-horizon scientific registry.
-- Extends research.research_runs. It does not replace those runs, and it does
-- not grant publication. Apply locally only. Do not apply this file to a host.

create table research.hypotheses (
  hypothesis_id text not null,
  version integer not null,
  proposition text not null,
  economic_rationale text not null,
  expected_mechanism text not null,
  expected_direction text not null,
  horizon text not null,
  falsification_criteria text not null,
  alternative_explanations jsonb not null,
  relevant_indicators jsonb not null,
  relevant_methodologies jsonb not null,
  target_instruments jsonb not null,
  initial_status text not null,
  amendment_rationale text,
  registered_at timestamptz not null,
  registered_by text not null,
  catalogue_signal_id text,
  publication_allowed boolean not null default false,
  primary key (hypothesis_id, version),
  constraint hypotheses_version_positive check (version >= 1),
  constraint hypotheses_amendment check (
    version = 1 or amendment_rationale is not null
  ),
  constraint hypotheses_status check (
    initial_status in (
      'proposed',
      'exploratory',
      'retrospective_only',
      'insufficient_data',
      'statistically_supported',
      'economically_useful',
      'rejected',
      'inconclusive',
      'superseded',
      'forward_validated'
    )
  ),
  constraint hypotheses_unpublished check (publication_allowed = false)
);

comment on table research.hypotheses is
  'Versioned hypothesis text. A later version is a new row. The original proposition is not overwritten.';

create table research.experiment_specifications (
  experiment_id text not null,
  version integer not null,
  category text not null,
  category_label text not null,
  specification jsonb not null,
  specification_hash text not null,
  frozen_at timestamptz not null,
  publication_allowed boolean not null default false,
  primary key (experiment_id, version),
  constraint experiment_specifications_version_positive check (version >= 1),
  constraint experiment_specifications_category check (
    (category = 'A' and category_label = 'historically_valid_point_in_time')
    or (category = 'B' and category_label = 'retrospective_economic_research')
    or (category = 'C' and category_label = 'price_only_simulator_research')
  ),
  constraint experiment_specifications_category_c_not_macro check (
    category <> 'C'
    or coalesce(
      specification->>'not_macroeconomic_investment_intelligence',
      'false'
    ) = 'true'
  ),
  constraint experiment_specifications_hash check (specification_hash ~ '^[0-9a-f]{64}$'),
  constraint experiment_specifications_unpublished check (publication_allowed = false)
);

comment on table research.experiment_specifications is
  'Frozen experiment specification. Category C is price-only simulator research and is not macroeconomic investment intelligence.';

comment on column research.experiment_specifications.category is
  'A is a historically valid point-in-time investment experiment. B is retrospective economic research. C is price-only simulator research.';

create table research.hypothesis_experiment_links (
  hypothesis_id text not null,
  hypothesis_version integer not null,
  experiment_id text not null,
  experiment_version integer not null,
  recorded_at timestamptz not null,
  primary key (hypothesis_id, hypothesis_version, experiment_id, experiment_version),
  foreign key (hypothesis_id, hypothesis_version)
    references research.hypotheses (hypothesis_id, version),
  foreign key (experiment_id, experiment_version)
    references research.experiment_specifications (experiment_id, version)
);

create table research.experiment_executions (
  execution_id text primary key,
  experiment_id text not null,
  experiment_version integer not null,
  state text not null,
  git_commit text not null,
  code_hash text not null,
  parameter_version_id text,
  input_manifest jsonb not null,
  macro_vintage_ids jsonb not null,
  price_series_versions jsonb not null,
  library_versions jsonb not null,
  random_seed text,
  executed_at timestamptz not null,
  availability_cutoff timestamptz not null,
  simulation_start date,
  simulation_end date,
  artifact_sha256 text not null,
  reproduction_command text not null,
  validation_status text not null,
  configuration jsonb not null,
  supersedes_execution_id text,
  research_run_id text,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null default now(),
  foreign key (experiment_id, experiment_version)
    references research.experiment_specifications (experiment_id, version),
  foreign key (supersedes_execution_id)
    references research.experiment_executions (execution_id),
  foreign key (research_run_id)
    references research.research_runs (run_id),
  constraint experiment_executions_state check (
    state in ('succeeded', 'failed', 'blocked')
  ),
  constraint experiment_executions_hash check (
    code_hash ~ '^[0-9a-f]{64}$' and artifact_sha256 ~ '^[0-9a-f]{64}$'
  ),
  constraint experiment_executions_unpublished check (publication_allowed = false),
  constraint experiment_executions_no_gdp_vintage check (
    not (macro_vintage_ids ? 'bea.vintage.real_gdp.pct_preceding')
  )
);

comment on table research.experiment_executions is
  'One immutable execution. A re-run is a new row. publication_allowed stays false. The real GDP growth vintage is not a portfolio-decision input.';

comment on column research.experiment_executions.research_run_id is
  'Optional link to an existing macro research run. Portfolio simulations do not invent a research_runs row.';

create table research.evidence_records (
  evidence_id text primary key,
  execution_id text not null references research.experiment_executions (execution_id),
  evidence_kind text not null,
  content_sha256 text not null,
  body jsonb not null,
  recorded_at timestamptz not null,
  publication_allowed boolean not null default false,
  constraint evidence_records_kind check (
    evidence_kind in (
      'wealth_path',
      'trade_ledger',
      'cash_ledger',
      'reconciliation',
      'forgone_path',
      'negative_finding',
      'data_quality',
      'statistical_note'
    )
  ),
  constraint evidence_records_hash check (content_sha256 ~ '^[0-9a-f]{64}$'),
  constraint evidence_records_unpublished check (publication_allowed = false)
);

comment on table research.evidence_records is
  'Inspectable evidence for one execution. A rejected hypothesis keeps its evidence.';

create table research.scientific_claims (
  claim_id text not null,
  version integer not null,
  proposition text not null,
  status_at_claim text not null,
  eligibility_class text not null,
  statistical_validity text not null,
  economic_usefulness text not null,
  independent_validation text not null,
  remaining_uncertainty text not null,
  publication_eligible boolean not null default false,
  publication_allowed boolean not null default false,
  derivation text not null,
  reviewer_note text not null,
  recorded_at timestamptz not null,
  primary key (claim_id, version),
  constraint scientific_claims_version_positive check (version >= 1),
  constraint scientific_claims_status check (
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
      'forward_validated'
    )
  ),
  constraint scientific_claims_eligibility check (
    eligibility_class in (
      'not_an_investment_claim',
      'category_a_candidate',
      'category_b_retrospective',
      'category_c_price_only'
    )
  ),
  constraint scientific_claims_category_c_not_promoted check (
    eligibility_class <> 'category_c_price_only'
    or status_at_claim in (
      'proposed',
      'exploratory',
      'retrospective_only',
      'insufficient_data',
      'rejected',
      'inconclusive',
      'superseded'
    )
  ),
  constraint scientific_claims_derivation check (derivation = 'deterministic_criteria'),
  constraint scientific_claims_unpublished check (
    publication_allowed = false and publication_eligible = false
  )
);

comment on table research.scientific_claims is
  'A claim version is not an execution result. Status is copied from deterministic criteria. A language model does not assign it. Category C cannot be statistically supported, economically useful, or forward-validated.';

create table research.claim_evidence_links (
  claim_id text not null,
  claim_version integer not null,
  evidence_id text not null references research.evidence_records (evidence_id),
  relation text not null,
  recorded_at timestamptz not null,
  primary key (claim_id, claim_version, evidence_id, relation),
  foreign key (claim_id, claim_version)
    references research.scientific_claims (claim_id, version),
  constraint claim_evidence_links_relation check (
    relation in ('supports', 'contradicts', 'qualifies')
  )
);

create table research.claim_execution_links (
  claim_id text not null,
  claim_version integer not null,
  execution_id text not null references research.experiment_executions (execution_id),
  relation text not null,
  recorded_at timestamptz not null,
  primary key (claim_id, claim_version, execution_id, relation),
  foreign key (claim_id, claim_version)
    references research.scientific_claims (claim_id, version),
  constraint claim_execution_links_relation check (
    relation in ('supports', 'contradicts', 'qualifies')
  )
);

create table research.scientific_status_events (
  status_event_id text primary key,
  status_event_seq bigint generated always as identity,
  subject_kind text not null,
  subject_id text not null,
  subject_version integer,
  status text not null,
  rationale text not null,
  derivation text not null,
  recorded_at timestamptz not null,
  publication_allowed boolean not null default false,
  constraint scientific_status_events_kind check (
    subject_kind in ('hypothesis', 'experiment', 'claim')
  ),
  constraint scientific_status_events_status check (
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
      'forward_validated'
    )
  ),
  constraint scientific_status_events_derivation check (
    derivation = 'deterministic_criteria'
  ),
  constraint scientific_status_events_unpublished check (publication_allowed = false)
);

comment on table research.scientific_status_events is
  'Append-only scientific status. The latest event is the current status. Earlier evidence is not rewritten.';

create table research.research_dependencies (
  dependency_id text primary key,
  left_kind text not null,
  left_id text not null,
  right_kind text not null,
  right_id text not null,
  relation text not null,
  dataset_id text,
  indicator_id text,
  instrument_id text,
  methodology_id text,
  period_start date,
  period_end date,
  independent_confirmation boolean not null,
  detail text not null,
  recorded_at timestamptz not null,
  constraint research_dependencies_relation check (
    relation in (
      'shares_dataset',
      'overlaps_period',
      'shares_instrument',
      'shares_indicator',
      'shares_methodology',
      'restates',
      'same_contribution_schedule',
      'matched_control'
    )
  ),
  constraint research_dependencies_not_independent check (
    relation not in (
      'shares_dataset',
      'overlaps_period',
      'shares_instrument',
      'shares_indicator',
      'same_contribution_schedule',
      'matched_control'
    )
    or independent_confirmation = false
  )
);

comment on table research.research_dependencies is
  'Shared inputs and overlapping periods. Those links are not independent confirmations.';

create table research.candidate_design_rows (
  register_id text not null,
  register_version integer not null,
  source_filename text not null,
  source_sha256 text not null,
  source_bytes bigint not null,
  row_kind text not null,
  original_id text not null,
  payload jsonb not null,
  empirical_result boolean not null default false,
  disagreement_note text,
  imported_at timestamptz not null,
  publication_allowed boolean not null default false,
  primary key (
    register_id,
    register_version,
    source_sha256,
    row_kind,
    original_id
  ),
  constraint candidate_design_rows_version check (register_version >= 1),
  constraint candidate_design_rows_kind check (
    row_kind in ('file', 'scenario', 'signal', 'comparison', 'sheet')
  ),
  constraint candidate_design_rows_hash check (source_sha256 ~ '^[0-9a-f]{64}$'),
  constraint candidate_design_rows_not_a_result check (empirical_result = false),
  constraint candidate_design_rows_unpublished check (publication_allowed = false)
);

comment on table research.candidate_design_rows is
  'Versioned candidate research-design register. Original scenario and signal identifiers are preserved. A row is not an empirical result.';

create table research.research_family_gates (
  register_id text not null,
  family_name text not null,
  gate text not null,
  reason text not null,
  recorded_at timestamptz not null,
  publication_allowed boolean not null default false,
  primary key (register_id, family_name),
  constraint research_family_gates_gate check (
    gate in ('blocked', 'design_only_not_executed')
  ),
  constraint research_family_gates_unpublished check (publication_allowed = false)
);

comment on table research.research_family_gates is
  'Why a catalogue family is blocked or still design-only. This is not an execution count.';

create index candidate_design_rows_original_idx
  on research.candidate_design_rows (row_kind, original_id);

create index scientific_status_events_subject_idx
  on research.scientific_status_events (subject_kind, subject_id, status_event_seq);

create view research.current_scientific_status as
select distinct on (subject_kind, subject_id)
  subject_kind,
  subject_id,
  subject_version,
  status,
  rationale,
  recorded_at,
  status_event_id,
  status_event_seq
from research.scientific_status_events
order by subject_kind, subject_id, status_event_seq desc;

comment on view research.current_scientific_status is
  'Latest scientific status for a subject. It does not replace the immutable evidence or the claim version that recorded an earlier status.';

create view research.long_horizon_progress as
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
  ) as executions_published;

comment on view research.long_horizon_progress is
  'Registered design rows are not executed simulations. This view has no completion percentage.';

create or replace function research.reject_gdp_portfolio_replay()
returns trigger
language plpgsql
set search_path = research, pg_temp
as $$
begin
  if new.macro_vintage_ids ? 'bea.vintage.real_gdp.pct_preceding' then
    raise exception
      'bea.vintage.real_gdp.pct_preceding is not a portfolio-decision input';
  end if;
  return new;
end;
$$;

create trigger experiment_executions_reject_gdp_replay
before insert on research.experiment_executions
for each row
execute function research.reject_gdp_portfolio_replay();

create or replace function research.require_next_version()
returns trigger
language plpgsql
set search_path = research, pg_temp
as $$
declare
  previous_max integer;
begin
  if tg_table_name = 'hypotheses' then
    select coalesce(max(version), 0) into previous_max
    from research.hypotheses
    where hypothesis_id = new.hypothesis_id;
  elsif tg_table_name = 'experiment_specifications' then
    select coalesce(max(version), 0) into previous_max
    from research.experiment_specifications
    where experiment_id = new.experiment_id;
  elsif tg_table_name = 'scientific_claims' then
    select coalesce(max(version), 0) into previous_max
    from research.scientific_claims
    where claim_id = new.claim_id;
  else
    raise exception 'require_next_version is not defined for %', tg_table_name;
  end if;
  if new.version <> previous_max + 1 then
    raise exception
      'research.% versions must append as the next integer', tg_table_name;
  end if;
  return new;
end;
$$;

create trigger hypotheses_require_next_version
before insert on research.hypotheses
for each row
execute function research.require_next_version();

create trigger experiment_specifications_require_next_version
before insert on research.experiment_specifications
for each row
execute function research.require_next_version();

create trigger scientific_claims_require_next_version
before insert on research.scientific_claims
for each row
execute function research.require_next_version();

create trigger hypotheses_deny_mutation
before update or delete on research.hypotheses
for each row
execute function research.deny_row_mutation();

create trigger experiment_specifications_deny_mutation
before update or delete on research.experiment_specifications
for each row
execute function research.deny_row_mutation();

create trigger hypothesis_experiment_links_deny_mutation
before update or delete on research.hypothesis_experiment_links
for each row
execute function research.deny_row_mutation();

create trigger experiment_executions_deny_mutation
before update or delete on research.experiment_executions
for each row
execute function research.deny_row_mutation();

create trigger evidence_records_deny_mutation
before update or delete on research.evidence_records
for each row
execute function research.deny_row_mutation();

create trigger scientific_claims_deny_mutation
before update or delete on research.scientific_claims
for each row
execute function research.deny_row_mutation();

create trigger claim_evidence_links_deny_mutation
before update or delete on research.claim_evidence_links
for each row
execute function research.deny_row_mutation();

create trigger claim_execution_links_deny_mutation
before update or delete on research.claim_execution_links
for each row
execute function research.deny_row_mutation();

create trigger scientific_status_events_deny_mutation
before update or delete on research.scientific_status_events
for each row
execute function research.deny_row_mutation();

create trigger research_dependencies_deny_mutation
before update or delete on research.research_dependencies
for each row
execute function research.deny_row_mutation();

create trigger candidate_design_rows_deny_mutation
before update or delete on research.candidate_design_rows
for each row
execute function research.deny_row_mutation();

create trigger research_family_gates_deny_mutation
before update or delete on research.research_family_gates
for each row
execute function research.deny_row_mutation();

revoke all on table research.hypotheses from public, anon, authenticated, service_role;
revoke all on table research.experiment_specifications from public, anon, authenticated, service_role;
revoke all on table research.hypothesis_experiment_links from public, anon, authenticated, service_role;
revoke all on table research.experiment_executions from public, anon, authenticated, service_role;
revoke all on table research.evidence_records from public, anon, authenticated, service_role;
revoke all on table research.scientific_claims from public, anon, authenticated, service_role;
revoke all on table research.claim_evidence_links from public, anon, authenticated, service_role;
revoke all on table research.claim_execution_links from public, anon, authenticated, service_role;
revoke all on table research.scientific_status_events from public, anon, authenticated, service_role;
revoke all on table research.research_dependencies from public, anon, authenticated, service_role;
revoke all on table research.candidate_design_rows from public, anon, authenticated, service_role;
revoke all on table research.research_family_gates from public, anon, authenticated, service_role;

grant select, insert on table research.hypotheses to research_writer;
grant select, insert on table research.experiment_specifications to research_writer;
grant select, insert on table research.hypothesis_experiment_links to research_writer;
grant select, insert on table research.experiment_executions to research_writer;
grant select, insert on table research.evidence_records to research_writer;
grant select, insert on table research.scientific_claims to research_writer;
grant select, insert on table research.claim_evidence_links to research_writer;
grant select, insert on table research.claim_execution_links to research_writer;
grant select, insert on table research.scientific_status_events to research_writer;
grant select, insert on table research.research_dependencies to research_writer;
grant select, insert on table research.candidate_design_rows to research_writer;
grant select, insert on table research.research_family_gates to research_writer;

grant usage, select on all sequences in schema research to research_writer;

grant select on table research.current_scientific_status to research_writer;
grant select on table research.long_horizon_progress to research_writer;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'research_reader') then
    execute 'grant select on table research.hypotheses to research_reader';
    execute 'grant select on table research.experiment_specifications to research_reader';
    execute 'grant select on table research.hypothesis_experiment_links to research_reader';
    execute 'grant select on table research.experiment_executions to research_reader';
    execute 'grant select on table research.evidence_records to research_reader';
    execute 'grant select on table research.scientific_claims to research_reader';
    execute 'grant select on table research.claim_evidence_links to research_reader';
    execute 'grant select on table research.claim_execution_links to research_reader';
    execute 'grant select on table research.scientific_status_events to research_reader';
    execute 'grant select on table research.research_dependencies to research_reader';
    execute 'grant select on table research.candidate_design_rows to research_reader';
    execute 'grant select on table research.research_family_gates to research_reader';
    execute 'grant select on table research.current_scientific_status to research_reader';
    execute 'grant select on table research.long_horizon_progress to research_reader';
  end if;
end $$;
