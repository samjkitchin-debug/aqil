-- Macro events and structural theme assessments.
-- Append-only research records. Local migration only.
-- Do not apply this file to the hosted project.

create or replace function research.text_array_is_short_labels(p_items text[], p_max integer)
returns boolean
language sql
immutable
set search_path = research, pg_temp
as $$
  select p_items is not null
    and cardinality(p_items) <= p_max
    and not exists (
      select 1
      from unnest(p_items) as item
      where item is null
        or char_length(btrim(item)) < 1
        or char_length(item) > 80
    );
$$;

create or replace function research.macro_indicator_ids_allowed(p_ids text[])
returns boolean
language sql
immutable
set search_path = research, pg_temp
as $$
  select p_ids is not null
    and cardinality(p_ids) <= 10
    and cardinality(p_ids) = (
      select count(distinct item)
      from unnest(p_ids) as item
    )
    and p_ids <@ array[
      'bls_cps_unemployment_rate',
      'bls_ces_total_nonfarm_payrolls',
      'bls_jolts_total_nonfarm_job_openings',
      'bls_cpi_u_all_items',
      'federal_reserve_g17_total_ip',
      'federal_reserve_sloos_cil',
      'federal_reserve_h8_bank_credit',
      'federal_reserve_h15_federal_funds_effective',
      'federal_reserve_h15_treasury_10y_constant_maturity',
      'ecb_sdw_hicp_sa'
    ]::text[];
$$;

comment on function research.macro_indicator_ids_allowed(text[]) is
  'The ten MACRO_SERIES source ids. Plausible channels only, not a measured effect.';

-- ---------------------------------------------------------------------------
-- macro_events
-- ---------------------------------------------------------------------------

create table research.macro_events (
  event_id uuid primary key default gen_random_uuid(),
  schema_version text not null default '1.0',
  event_key text not null,
  category text not null,
  epistemic_class text not null,
  claim_scope text not null,
  summary text not null,
  country text,
  region text,
  industries text[] not null default '{}',
  event_on date not null,
  event_dates_stated text not null,
  indicator_source_ids text[] not null default '{}',
  channel_note text,
  surface_on_today boolean not null default false,
  surface_reason text,
  surfaced_at timestamptz,
  record_class text not null,
  monitoring text not null default 'manual',
  publication_allowed boolean not null default false,
  investment_implication text not null,
  recorded_at timestamptz not null default now(),
  constraint macro_events_schema_version check (schema_version = '1.0'),
  constraint macro_events_event_key check (event_key ~ '^[a-z0-9_]{1,80}$'),
  constraint macro_events_event_key_unique unique (event_key),
  constraint macro_events_category check (category ~ '^[a-z0-9_]{1,80}$'),
  constraint macro_events_epistemic_class check (
    epistemic_class in (
      'confirmed_event',
      'reported_allegation',
      'forecast',
      'interpretation'
    )
  ),
  constraint macro_events_claim_scope check (
    claim_scope in ('policy_action_stated', 'publication_recorded')
  ),
  constraint macro_events_summary check (
    char_length(btrim(summary)) between 1 and 500
    and not research.text_contains_secret_pattern(summary)
  ),
  constraint macro_events_country check (
    country is null
    or (
      char_length(btrim(country)) between 1 and 80
      and not research.text_contains_secret_pattern(country)
    )
  ),
  constraint macro_events_region check (
    region is null
    or (
      char_length(btrim(region)) between 1 and 80
      and not research.text_contains_secret_pattern(region)
    )
  ),
  constraint macro_events_industries check (
    research.text_array_is_short_labels(industries, 12)
  ),
  constraint macro_events_dates_stated check (
    char_length(btrim(event_dates_stated)) between 1 and 400
    and not research.text_contains_secret_pattern(event_dates_stated)
  ),
  constraint macro_events_indicator_ids check (
    research.macro_indicator_ids_allowed(indicator_source_ids)
  ),
  constraint macro_events_channel_note check (
    (
      cardinality(indicator_source_ids) = 0
      and channel_note is null
    )
    or (
      cardinality(indicator_source_ids) > 0
      and channel_note is not null
      and char_length(btrim(channel_note)) between 20 and 400
      and channel_note ~* 'plausible channel'
      and channel_note ~* 'not a measured effect'
      and not research.text_contains_secret_pattern(channel_note)
    )
  ),
  constraint macro_events_surface_pair check (
    (surface_reason is null and surfaced_at is null)
    or (
      surface_reason is not null
      and surfaced_at is not null
      and char_length(btrim(surface_reason)) >= 40
      and char_length(surface_reason) <= 500
      and not research.text_contains_secret_pattern(surface_reason)
    )
  ),
  constraint macro_events_surface_flag check (
    surface_on_today = false
    or (surface_reason is not null and surfaced_at is not null)
  ),
  constraint macro_events_record_class check (
    record_class in ('recorded', 'synthetic_fixture')
  ),
  constraint macro_events_monitoring check (monitoring = 'manual'),
  constraint macro_events_publication_allowed check (publication_allowed = false),
  constraint macro_events_investment_implication check (
    investment_implication in ('no_action', 'insufficient_evidence')
  )
);

comment on table research.macro_events is
  'One manually registered event. event_on is the date the event concerns, not the source published_at. Summary is short and is not a document body. Local only. Do not apply this table to the hosted project.';

comment on column research.macro_events.indicator_source_ids is
  'Plausible indicator channels limited to the ten live MACRO_SERIES ids. Not a measured effect.';

comment on column research.macro_events.channel_note is
  'Required when indicator ids are present. Must describe a plausible channel, not a measured effect.';

comment on column research.macro_events.surface_on_today is
  'Today shows a recorded row only when this is true, a reason is stored, and a date is inside 45 days.';

comment on column research.macro_events.record_class is
  'recorded is visible to the web loader. synthetic_fixture is for tests and must not be selected there.';

create index macro_events_event_on_idx
  on research.macro_events (event_on desc);

-- ---------------------------------------------------------------------------
-- macro_event_evidence
-- ---------------------------------------------------------------------------

create table research.macro_event_evidence (
  evidence_id uuid primary key default gen_random_uuid(),
  event_id uuid not null references research.macro_events (event_id),
  update_id uuid not null references research.sourced_updates (update_id),
  role text not null,
  cluster_key text not null,
  recorded_at timestamptz not null default now(),
  constraint macro_event_evidence_role check (
    role in (
      'primary',
      'secondary',
      'supporting',
      'conflicting',
      'subsequent_development'
    )
  ),
  constraint macro_event_evidence_cluster_key check (
    cluster_key ~ '^[A-Za-z0-9_.:/-]{1,200}$'
  ),
  constraint macro_event_evidence_event_update_key unique (event_id, update_id),
  constraint macro_event_evidence_origin_role_key unique (event_id, cluster_key, role)
);

comment on table research.macro_event_evidence is
  'Link from an event to an existing sourced update. Independent confirmation is a query of distinct cluster_key, not a stored score.';

create index macro_event_evidence_event_idx
  on research.macro_event_evidence (event_id);

-- A confirmed event cannot commit without primary evidence.
-- policy_action_stated cannot rest only on a central-bank press release.
create or replace function research.enforce_macro_event_registration()
returns trigger
language plpgsql
set search_path = research, pg_temp
as $$
declare
  v_event_id uuid;
  v_class text;
  v_scope text;
  v_primary_sources text[];
begin
  v_event_id := new.event_id;

  select epistemic_class, claim_scope
  into v_class, v_scope
  from research.macro_events
  where event_id = v_event_id;

  if v_class is null then
    return null;
  end if;

  select coalesce(array_agg(distinct su.source_id), array[]::text[])
  into v_primary_sources
  from research.macro_event_evidence ev
  join research.sourced_updates su on su.update_id = ev.update_id
  where ev.event_id = v_event_id
    and ev.role = 'primary';

  if v_class = 'confirmed_event' and cardinality(v_primary_sources) = 0 then
    raise exception 'confirmed_event requires at least one primary evidence row'
      using errcode = '23514';
  end if;

  if v_scope = 'policy_action_stated'
    and cardinality(v_primary_sources) > 0
    and v_primary_sources <@ array[
      'federal_reserve_monetary_press',
      'ecb_monetary_press'
    ]::text[]
  then
    raise exception 'policy_action_stated cannot use only a central-bank press release as primary evidence'
      using errcode = '23514';
  end if;

  return null;
end;
$$;

comment on function research.enforce_macro_event_registration() is
  'Deferred check for one registration transaction. Confirmed events need primary evidence. A central-bank press release alone is not a stated policy action.';

create constraint trigger macro_events_registration_check
after insert on research.macro_events
deferrable initially deferred
for each row
execute function research.enforce_macro_event_registration();

create constraint trigger macro_event_evidence_registration_check
after insert on research.macro_event_evidence
deferrable initially deferred
for each row
execute function research.enforce_macro_event_registration();

create trigger macro_events_deny_mutation
before update or delete on research.macro_events
for each row
execute function research.deny_row_mutation();

create trigger macro_event_evidence_deny_mutation
before update or delete on research.macro_event_evidence
for each row
execute function research.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- theme_assessments
-- ---------------------------------------------------------------------------

create table research.theme_assessments (
  assessment_id uuid primary key default gen_random_uuid(),
  schema_version text not null default '1.0',
  theme_key text not null,
  supersedes_assessment_id uuid,
  real_economy_activity text not null,
  earnings text not null,
  market_prices text not null,
  media_attention text not null,
  publication_allowed boolean not null default false,
  record_class text not null,
  recorded_at timestamptz not null default now(),
  constraint theme_assessments_schema_version check (schema_version = '1.0'),
  constraint theme_assessments_theme_key check (theme_key = 'ai_infrastructure_investment'),
  constraint theme_assessments_real_economy check (
    char_length(btrim(real_economy_activity)) between 10 and 800
    and not research.text_contains_secret_pattern(real_economy_activity)
  ),
  constraint theme_assessments_earnings check (
    char_length(btrim(earnings)) between 10 and 800
    and not research.text_contains_secret_pattern(earnings)
  ),
  constraint theme_assessments_market_prices check (
    char_length(btrim(market_prices)) between 10 and 800
    and not research.text_contains_secret_pattern(market_prices)
  ),
  constraint theme_assessments_media check (
    char_length(btrim(media_attention)) between 10 and 800
    and not research.text_contains_secret_pattern(media_attention)
  ),
  constraint theme_assessments_publication_allowed check (publication_allowed = false),
  constraint theme_assessments_record_class check (
    record_class in ('recorded', 'synthetic_fixture')
  ),
  constraint theme_assessments_not_self check (
    supersedes_assessment_id is null or supersedes_assessment_id <> assessment_id
  ),
  constraint theme_assessments_supersedes_fkey
    foreign key (supersedes_assessment_id)
    references research.theme_assessments (assessment_id)
);

create unique index theme_assessments_one_successor_idx
  on research.theme_assessments (supersedes_assessment_id)
  where supersedes_assessment_id is not null;

comment on table research.theme_assessments is
  'Append-only theme dossier. A later row points at the prior row. The prior row is not rewritten. No strength, confidence or gauge. Local only. Do not apply this table to the hosted project.';

create or replace function research.enforce_theme_supersession()
returns trigger
language plpgsql
set search_path = research, pg_temp
as $$
declare
  v_prior_theme text;
begin
  if new.supersedes_assessment_id is null then
    return new;
  end if;
  if new.supersedes_assessment_id = new.assessment_id then
    raise exception 'a theme assessment cannot supersede itself';
  end if;

  select theme_key
  into v_prior_theme
  from research.theme_assessments
  where assessment_id = new.supersedes_assessment_id;

  if v_prior_theme is null then
    raise exception 'unknown supersedes_assessment_id %', new.supersedes_assessment_id;
  end if;
  if v_prior_theme is distinct from new.theme_key then
    raise exception 'supersession must keep the same theme_key';
  end if;
  return new;
end;
$$;

create trigger theme_assessments_supersession
before insert on research.theme_assessments
for each row
execute function research.enforce_theme_supersession();

create trigger theme_assessments_deny_mutation
before update or delete on research.theme_assessments
for each row
execute function research.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- theme_dimension_evidence
-- ---------------------------------------------------------------------------

create or replace function research.theme_measure_fits_dimension(
  p_dimension text,
  p_measure_kind text
)
returns boolean
language sql
immutable
set search_path = research, pg_temp
as $$
  select case
    when p_measure_kind = 'none' then true
    when p_dimension = 'infrastructure_investment'
      and p_measure_kind in ('actual_capital_expenditure', 'forecast_spending') then true
    when p_dimension = 'commercial_adoption'
      and p_measure_kind = 'commercial_adoption' then true
    when p_dimension = 'semiconductor_equipment_demand'
      and p_measure_kind = 'infrastructure_demand' then true
    when p_dimension = 'earnings_cash_flow'
      and p_measure_kind in ('revenue', 'earnings') then true
    when p_dimension = 'market_breadth_relative_performance'
      and p_measure_kind = 'equity_price' then true
    else false
  end;
$$;

comment on function research.theme_measure_fits_dimension(text, text) is
  'Rejects interchangeable measures. equity_price is not infrastructure-investment evidence. actual_spending is not accepted for any dimension in this slice.';

create table research.theme_dimension_evidence (
  dimension_evidence_id uuid primary key default gen_random_uuid(),
  assessment_id uuid not null references research.theme_assessments (assessment_id),
  dimension text not null,
  status text not null,
  measure_kind text not null,
  explanation text not null,
  update_id uuid references research.sourced_updates (update_id),
  amount text,
  unit text,
  period_start date,
  period_end date,
  reporting_entity text,
  filed_at date,
  relationship text,
  recorded_at timestamptz not null default now(),
  constraint theme_dimension_dimension check (
    dimension in (
      'infrastructure_investment',
      'commercial_adoption',
      'semiconductor_equipment_demand',
      'earnings_cash_flow',
      'market_breadth_relative_performance',
      'financing_sustainability'
    )
  ),
  constraint theme_dimension_status check (
    status in (
      'available',
      'stale',
      'insufficient',
      'contradictory',
      'not_yet_monitored'
    )
  ),
  constraint theme_dimension_measure_kind check (
    measure_kind in (
      'actual_capital_expenditure',
      'forecast_spending',
      'actual_spending',
      'infrastructure_demand',
      'commercial_adoption',
      'revenue',
      'earnings',
      'equity_price',
      'none'
    )
  ),
  constraint theme_dimension_measure_fits check (
    research.theme_measure_fits_dimension(dimension, measure_kind)
  ),
  constraint theme_dimension_explanation check (
    char_length(btrim(explanation)) between 10 and 800
    and not research.text_contains_secret_pattern(explanation)
  ),
  constraint theme_dimension_relationship check (
    relationship is null or relationship in ('supports', 'contradicts')
  ),
  constraint theme_dimension_not_monitored check (
    status <> 'not_yet_monitored'
    or (
      update_id is null
      and measure_kind = 'none'
      and relationship is null
      and amount is null
    )
  ),
  constraint theme_dimension_available check (
    status <> 'available'
    or (
      update_id is not null
      and measure_kind <> 'none'
      and relationship in ('supports', 'contradicts')
      and char_length(btrim(explanation)) >= 20
    )
  ),
  constraint theme_dimension_contradictory check (
    status <> 'contradictory'
    or relationship = 'contradicts'
  ),
  constraint theme_dimension_amount_shape check (
    (
      amount is null
      and unit is null
      and period_start is null
      and period_end is null
      and reporting_entity is null
      and filed_at is null
    )
    or (
      amount is not null
      and amount ~ '^[0-9]+(\.[0-9]+)?$'
      and unit is not null
      and char_length(btrim(unit)) between 1 and 40
      and period_start is not null
      and period_end is not null
      and period_end > period_start
      and reporting_entity is not null
      and char_length(btrim(reporting_entity)) between 1 and 200
      and filed_at is not null
      and not research.text_contains_secret_pattern(reporting_entity)
    )
  )
);

create unique index theme_dimension_evidence_open_dimension_key
  on research.theme_dimension_evidence (assessment_id, dimension)
  where period_start is null;

create unique index theme_dimension_evidence_period_key
  on research.theme_dimension_evidence (assessment_id, dimension, period_start, period_end)
  where period_start is not null;

comment on table research.theme_dimension_evidence is
  'One row supports one theme dimension. available requires a sourced update and an explanation. Amounts are filing facts, not macro observations.';

create trigger theme_dimension_evidence_deny_mutation
before update or delete on research.theme_dimension_evidence
for each row
execute function research.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- Grants match research.sourced_updates: worker read/append, no API role.
-- ---------------------------------------------------------------------------

revoke all on table research.macro_events from public;
revoke all on table research.macro_events from anon;
revoke all on table research.macro_events from authenticated;
revoke all on table research.macro_events from service_role;
grant select, insert on table research.macro_events to research_writer;

revoke all on table research.macro_event_evidence from public;
revoke all on table research.macro_event_evidence from anon;
revoke all on table research.macro_event_evidence from authenticated;
revoke all on table research.macro_event_evidence from service_role;
grant select, insert on table research.macro_event_evidence to research_writer;

revoke all on table research.theme_assessments from public;
revoke all on table research.theme_assessments from anon;
revoke all on table research.theme_assessments from authenticated;
revoke all on table research.theme_assessments from service_role;
grant select, insert on table research.theme_assessments to research_writer;

revoke all on table research.theme_dimension_evidence from public;
revoke all on table research.theme_dimension_evidence from anon;
revoke all on table research.theme_dimension_evidence from authenticated;
revoke all on table research.theme_dimension_evidence from service_role;
grant select, insert on table research.theme_dimension_evidence to research_writer;

revoke all on function research.text_array_is_short_labels(text[], integer) from public;
revoke all on function research.text_array_is_short_labels(text[], integer) from anon;
revoke all on function research.text_array_is_short_labels(text[], integer) from authenticated;
revoke all on function research.text_array_is_short_labels(text[], integer) from service_role;
grant execute on function research.text_array_is_short_labels(text[], integer) to research_writer;

revoke all on function research.macro_indicator_ids_allowed(text[]) from public;
revoke all on function research.macro_indicator_ids_allowed(text[]) from anon;
revoke all on function research.macro_indicator_ids_allowed(text[]) from authenticated;
revoke all on function research.macro_indicator_ids_allowed(text[]) from service_role;
grant execute on function research.macro_indicator_ids_allowed(text[]) to research_writer;

revoke all on function research.enforce_macro_event_registration() from public;
revoke all on function research.enforce_macro_event_registration() from anon;
revoke all on function research.enforce_macro_event_registration() from authenticated;
revoke all on function research.enforce_macro_event_registration() from service_role;
grant execute on function research.enforce_macro_event_registration() to research_writer;

revoke all on function research.enforce_theme_supersession() from public;
revoke all on function research.enforce_theme_supersession() from anon;
revoke all on function research.enforce_theme_supersession() from authenticated;
revoke all on function research.enforce_theme_supersession() from service_role;
grant execute on function research.enforce_theme_supersession() to research_writer;

revoke all on function research.theme_measure_fits_dimension(text, text) from public;
revoke all on function research.theme_measure_fits_dimension(text, text) from anon;
revoke all on function research.theme_measure_fits_dimension(text, text) from authenticated;
revoke all on function research.theme_measure_fits_dimension(text, text) from service_role;
grant execute on function research.theme_measure_fits_dimension(text, text) to research_writer;
