-- ETF research protocol trials.
-- Extends the local research schema. It does not edit EVT-DEF-001.
-- Apply locally only. Do not apply this file to a hosted project.

alter table research.market_events drop constraint market_events_family;
alter table research.market_events add constraint market_events_family check (
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
    'flat_market',
    'sustained_decline',
    'persistent_bear',
    'failed_recovery',
    'trend_reversal',
    'volatility_transition'
  )
);

create table research.etf_protocol_specifications (
  specification_id text not null,
  version integer not null,
  specification jsonb not null,
  specification_hash text not null,
  frozen_at timestamptz not null,
  publication_allowed boolean not null default false,
  primary key (specification_id, version),
  constraint etf_protocol_specifications_version_positive check (version >= 1),
  constraint etf_protocol_specifications_hash check (specification_hash ~ '^[0-9a-f]{64}$'),
  constraint etf_protocol_specifications_unpublished check (publication_allowed = false)
);

comment on table research.etf_protocol_specifications is
  'Frozen ETF research protocol. A later version is a new row. publication_allowed stays false.';

create table research.etf_protocol_trials (
  trial_id text primary key,
  specification_id text not null,
  specification_version integer not null,
  specification_hash text not null,
  dossier_id text not null,
  symbol text not null,
  feature text not null,
  transform text not null,
  horizon_label text not null,
  outcome text not null,
  statistic text not null,
  eligibility text not null,
  result_text text,
  refusal_reason text,
  effect_text text,
  p_value_text text,
  result_status text,
  detail text not null,
  publication_allowed boolean not null default false,
  recorded_at timestamptz not null,
  foreign key (specification_id, specification_version)
    references research.etf_protocol_specifications (specification_id, version),
  constraint etf_protocol_trials_hash check (specification_hash ~ '^[0-9a-f]{64}$'),
  constraint etf_protocol_trials_symbol check (symbol in ('VWRA', 'EIMI', 'EIMI-VWRA')),
  constraint etf_protocol_trials_dossier check (
    dossier_id in ('LH-X-005', 'LH-X-006', 'LH-X-007')
  ),
  constraint etf_protocol_trials_eligibility check (
    eligibility in (
      'category_c_price_only',
      'category_b_retrospective',
      'point_in_time_indicator',
      'not_a_method_replay',
      'not_estimable'
    )
  ),
  constraint etf_protocol_trials_result_or_refusal check (
    (result_text is null) <> (refusal_reason is null)
  ),
  constraint etf_protocol_trials_refusal_has_no_effect check (
    refusal_reason is null or effect_text is null
  ),
  constraint etf_protocol_trials_method_null check (
    eligibility <> 'not_a_method_replay'
    or (
      effect_text is null
      and result_text is null
      and p_value_text is null
    )
  ),
  constraint etf_protocol_trials_search_null check (
    eligibility <> 'not_estimable' or effect_text is null
  ),
  constraint etf_protocol_trials_category_c_not_promoted check (
    eligibility <> 'category_c_price_only'
    or result_status is null
    or result_status in (
      'insufficient_data',
      'rejected',
      'no_incremental_information',
      'inconclusive'
    )
  ),
  constraint etf_protocol_trials_unpublished check (publication_allowed = false)
);

comment on table research.etf_protocol_trials is
  'Append-only ETF protocol trials, including refused rows. publication_allowed stays false. A category C row cannot record a promoted status.';

create index etf_protocol_trials_lookup_idx
  on research.etf_protocol_trials (symbol, feature, outcome);

create view research.etf_protocol_coverage as
select
  symbol,
  feature,
  transform,
  horizon_label,
  outcome,
  statistic,
  eligibility,
  result_text,
  refusal_reason,
  effect_text,
  result_status,
  publication_allowed
from research.etf_protocol_trials;

comment on view research.etf_protocol_coverage is
  'Reverse lookup by symbol, feature, and outcome. Refused rows and null effects stay visible.';

create view research.etf_protocol_dossier_summary as
select
  dossier_id,
  symbol,
  count(*)::integer as trial_count,
  count(*) filter (where refusal_reason is not null)::integer as refused_count,
  count(*) filter (where effect_text is not null)::integer as effect_count,
  bool_or(publication_allowed) as any_published
from research.etf_protocol_trials
group by dossier_id, symbol;

comment on view research.etf_protocol_dossier_summary is
  'Counts for one dossier. It is not a second fact table.';

create trigger etf_protocol_specifications_deny_mutation
before update or delete on research.etf_protocol_specifications
for each row execute function research.deny_row_mutation();

create trigger etf_protocol_trials_deny_mutation
before update or delete on research.etf_protocol_trials
for each row execute function research.deny_row_mutation();

revoke all on table research.etf_protocol_specifications from public, anon, authenticated, service_role;
revoke all on table research.etf_protocol_trials from public, anon, authenticated, service_role;
revoke all on table research.etf_protocol_coverage from public, anon, authenticated, service_role;
revoke all on table research.etf_protocol_dossier_summary from public, anon, authenticated, service_role;

grant select, insert on table research.etf_protocol_specifications to research_writer;
grant select, insert on table research.etf_protocol_trials to research_writer;
grant select on table research.etf_protocol_coverage to research_writer;
grant select on table research.etf_protocol_dossier_summary to research_writer;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'research_reader') then
    execute 'grant select on table research.etf_protocol_specifications to research_reader';
    execute 'grant select on table research.etf_protocol_trials to research_reader';
    execute 'grant select on table research.etf_protocol_coverage to research_reader';
    execute 'grant select on table research.etf_protocol_dossier_summary to research_reader';
  end if;
end $$;
