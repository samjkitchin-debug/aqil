-- ETF instruments. Private schema — not exposed via Supabase Data API.
-- Apply only to the local database aqil_etf. Do not apply this file to the
-- preserved database postgres, and do not add instruments to [api].schemas.

create schema instruments;

comment on schema instruments is
  'ETF umbrella, share class, listing, and evidence. Not in [api].schemas.';

revoke all on schema instruments from public;
revoke all on schema instruments from anon;
revoke all on schema instruments from authenticated;
revoke all on schema instruments from service_role;

grant usage on schema instruments to research_writer;

-- ---------------------------------------------------------------------------
-- Legal structure. Trading currency, base currency, hedge status, and
-- distribution policy are separate columns.
-- ---------------------------------------------------------------------------

create table instruments.umbrellas (
  umbrella_id uuid primary key default gen_random_uuid(),
  legal_name text not null,
  domicile_iso2 text,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint umbrellas_legal_name_present check (length(btrim(legal_name)) > 0),
  constraint umbrellas_domicile_iso2 check (
    domicile_iso2 is null or domicile_iso2 ~ '^[A-Z]{2}$'
  )
);

create table instruments.sub_funds (
  sub_fund_id uuid primary key default gen_random_uuid(),
  umbrella_id uuid not null references instruments.umbrellas (umbrella_id),
  legal_name text not null,
  base_currency text not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint sub_funds_legal_name_present check (length(btrim(legal_name)) > 0),
  constraint sub_funds_base_currency check (base_currency ~ '^[A-Z]{3}$')
);

comment on column instruments.sub_funds.base_currency is
  'Sub-fund base currency. Not the listing trading currency and not hedge status.';

create table instruments.share_classes (
  share_class_id uuid primary key default gen_random_uuid(),
  sub_fund_id uuid not null references instruments.sub_funds (sub_fund_id),
  isin text not null,
  distribution_policy text not null,
  hedge_status text not null,
  inception_date date,
  evidence_status text not null default 'unverified',
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint share_classes_isin_unique unique (isin),
  constraint share_classes_isin_format check (isin ~ '^[A-Z]{2}[A-Z0-9]{9}[0-9]$'),
  constraint share_classes_distribution_policy check (
    distribution_policy in ('accumulating', 'distributing', 'unknown')
  ),
  constraint share_classes_hedge_status check (
    hedge_status in ('hedged', 'unhedged', 'unknown')
  ),
  constraint share_classes_evidence_status check (
    evidence_status in ('unverified', 'cited', 'unavailable', 'insufficient')
  )
);

comment on table instruments.share_classes is
  'One row per ISIN. A ticker change does not insert another share class.';

comment on column instruments.share_classes.hedge_status is
  'Separate from base currency, distribution policy, and listing trading currency.';

create table instruments.listings (
  listing_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  mic text not null,
  trading_currency text not null,
  ticker text not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint listings_venue_key unique (share_class_id, mic, trading_currency, ticker),
  constraint listings_mic check (mic ~ '^[A-Z0-9]{4}$'),
  constraint listings_trading_currency check (trading_currency ~ '^[A-Z]{3}$'),
  constraint listings_ticker_present check (length(btrim(ticker)) > 0)
);

comment on column instruments.listings.trading_currency is
  'Currency of this listing. Not the sub-fund base currency.';

-- Ticker and other identifier changes append. They do not create a share class.
create table instruments.identifier_history (
  identifier_history_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  listing_id uuid references instruments.listings (listing_id),
  identifier_kind text not null,
  identifier_value text not null,
  effective_on date not null,
  source_id text not null,
  source_locator text not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint identifier_history_kind check (
    identifier_kind in ('ticker', 'isin', 'mic')
  ),
  constraint identifier_history_value_present check (length(btrim(identifier_value)) > 0),
  constraint identifier_history_source_present check (
    length(btrim(source_id)) > 0 and length(btrim(source_locator)) > 0
  )
);

create index identifier_history_share_class_idx
  on instruments.identifier_history (share_class_id, recorded_at desc);

create table instruments.benchmarks (
  benchmark_id uuid primary key default gen_random_uuid(),
  provider_name text not null,
  benchmark_code text not null,
  benchmark_name text not null,
  currency text not null,
  return_convention text not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint benchmarks_identity unique (
    provider_name, benchmark_code, return_convention, currency
  ),
  constraint benchmarks_currency check (currency ~ '^[A-Z]{3}$'),
  constraint benchmarks_return_convention check (
    return_convention in ('price', 'total_return', 'net_total_return', 'unknown')
  ),
  constraint benchmarks_names_present check (
    length(btrim(provider_name)) > 0
    and length(btrim(benchmark_code)) > 0
    and length(btrim(benchmark_name)) > 0
  )
);

comment on table instruments.benchmarks is
  'Benchmark identity. A price index and a total-return index are different rows. Not a fund return.';

-- Cited facts such as TER stay absent until availability is cited.
-- characteristic_code benchmark_id stores the cited instruments.benchmarks id.
create table instruments.dated_characteristics (
  characteristic_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  as_of_date date not null,
  characteristic_code text not null,
  value_text text,
  unit text,
  availability text not null,
  source_id text,
  source_locator text,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint dated_characteristics_code_present check (length(btrim(characteristic_code)) > 0),
  constraint dated_characteristics_availability check (
    availability in ('cited', 'unavailable')
  ),
  constraint dated_characteristics_cited_value check (
    (
      availability = 'cited'
      and value_text is not null
      and source_id is not null
      and source_locator is not null
      and length(btrim(value_text)) > 0
      and length(btrim(source_id)) > 0
      and length(btrim(source_locator)) > 0
    )
    or (
      availability = 'unavailable'
      and value_text is null
    )
  )
);

create table instruments.holdings_snapshots (
  snapshot_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  as_of_date date not null,
  source_id text not null,
  source_locator text not null,
  rights_gate text not null,
  completeness text not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint holdings_snapshots_rights_gate check (rights_gate = 'permitted'),
  constraint holdings_snapshots_completeness check (
    completeness in ('full', 'partial', 'unknown')
  ),
  constraint holdings_snapshots_source_present check (
    length(btrim(source_id)) > 0 and length(btrim(source_locator)) > 0
  )
);

comment on column instruments.holdings_snapshots.rights_gate is
  'Only permitted holdings may be stored. Prohibited and unknown sources fail before insert.';

create table instruments.holdings_lines (
  line_id uuid primary key default gen_random_uuid(),
  snapshot_id uuid not null references instruments.holdings_snapshots (snapshot_id),
  line_number integer not null,
  holding_name text not null,
  weight numeric,
  identifier text,
  constraint holdings_lines_identity unique (snapshot_id, line_number),
  constraint holdings_lines_number check (line_number > 0),
  constraint holdings_lines_name_present check (length(btrim(holding_name)) > 0)
);

create table instruments.exposure_snapshots (
  exposure_snapshot_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  as_of_date date not null,
  exposure_class text not null,
  weight numeric,
  evidence_status text not null,
  source_id text,
  source_locator text,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint exposure_snapshots_class_present check (length(btrim(exposure_class)) > 0),
  constraint exposure_snapshots_evidence_status check (
    evidence_status in ('unverified', 'cited', 'unavailable', 'insufficient')
  ),
  constraint exposure_snapshots_cited_source check (
    evidence_status <> 'cited'
    or (
      source_id is not null
      and source_locator is not null
      and length(btrim(source_id)) > 0
      and length(btrim(source_locator)) > 0
    )
  )
);

create table instruments.fund_returns (
  fund_return_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  period_start date not null,
  period_end date not null,
  currency text not null,
  return_type text not null,
  reinvestment text not null,
  value_text text not null,
  source_id text not null,
  source_locator text not null,
  series_role text not null default 'fund',
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint fund_returns_are_fund_series check (series_role = 'fund'),
  constraint fund_returns_period_order check (period_end >= period_start),
  constraint fund_returns_currency check (currency ~ '^[A-Z]{3}$'),
  constraint fund_returns_return_type check (
    return_type in ('nav', 'price', 'total_return', 'unknown')
  ),
  constraint fund_returns_reinvestment check (
    reinvestment in ('reinvested', 'not_reinvested', 'unknown')
  ),
  constraint fund_returns_value_present check (length(btrim(value_text)) > 0),
  constraint fund_returns_source_present check (
    length(btrim(source_id)) > 0 and length(btrim(source_locator)) > 0
  )
);

comment on table instruments.fund_returns is
  'Share-class fund return. Rejected before inception. Not a benchmark series.';

create table instruments.benchmark_returns (
  benchmark_return_id uuid primary key default gen_random_uuid(),
  benchmark_id uuid not null references instruments.benchmarks (benchmark_id),
  period_start date not null,
  period_end date not null,
  currency text not null,
  return_type text not null,
  reinvestment text not null,
  value_text text not null,
  source_id text not null,
  source_locator text not null,
  series_role text not null default 'benchmark',
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint benchmark_returns_are_benchmark_series check (series_role = 'benchmark'),
  constraint benchmark_returns_period_order check (period_end >= period_start),
  constraint benchmark_returns_currency check (currency ~ '^[A-Z]{3}$'),
  constraint benchmark_returns_return_type check (
    return_type in ('nav', 'price', 'total_return', 'unknown')
  ),
  constraint benchmark_returns_reinvestment check (
    reinvestment in ('reinvested', 'not_reinvested', 'unknown')
  ),
  constraint benchmark_returns_value_present check (length(btrim(value_text)) > 0),
  constraint benchmark_returns_source_present check (
    length(btrim(source_id)) > 0 and length(btrim(source_locator)) > 0
  )
);

comment on table instruments.benchmark_returns is
  'Benchmark return series. No share_class_id. Never the ETF own return.';

create table instruments.assessments (
  assessment_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  eligibility text not null,
  evidence_status text not null,
  statement text not null,
  source_id text,
  payload jsonb not null default '{}'::jsonb,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint assessments_eligibility check (
    eligibility in ('CORE', 'CONDITIONAL', 'EXCLUDED', 'UNKNOWN')
  ),
  constraint assessments_evidence_status check (
    evidence_status in ('unverified', 'cited', 'unavailable', 'insufficient')
  ),
  constraint assessments_missing_evidence_is_unknown check (
    evidence_status <> 'insufficient' or eligibility = 'UNKNOWN'
  ),
  constraint assessments_statement_present check (length(btrim(statement)) > 0),
  constraint assessments_payload_object check (jsonb_typeof(payload) = 'object')
);

comment on table instruments.assessments is
  'Append-only eligibility. Missing hard evidence stays UNKNOWN. No rank column.';

-- ---------------------------------------------------------------------------
-- Append-only history and the inception guard
-- ---------------------------------------------------------------------------

create or replace function instruments.deny_row_mutation()
returns trigger
language plpgsql
set search_path = instruments, pg_temp
as $$
begin
  raise exception 'instruments.% is append-only; % is not permitted', tg_table_name, tg_op;
end;
$$;

create trigger identifier_history_deny_mutation
before update or delete on instruments.identifier_history
for each row
execute function instruments.deny_row_mutation();

create trigger assessments_deny_mutation
before update or delete on instruments.assessments
for each row
execute function instruments.deny_row_mutation();

create or replace function instruments.reject_pre_inception_fund_return()
returns trigger
language plpgsql
set search_path = instruments, pg_temp
as $$
declare
  inception date;
begin
  select inception_date
    into inception
  from instruments.share_classes
  where share_class_id = new.share_class_id;

  if not found then
    raise exception 'fund return refused: share class % does not exist', new.share_class_id;
  end if;

  if inception is null then
    raise exception 'fund return refused: share class inception date is unknown';
  end if;

  if new.period_start < inception or new.period_end < inception then
    raise exception 'fund return refused: period is before share class inception';
  end if;

  return new;
end;
$$;

create trigger fund_returns_reject_pre_inception
before insert or update on instruments.fund_returns
for each row
execute function instruments.reject_pre_inception_fund_return();

-- ---------------------------------------------------------------------------
-- Privileges. Same Data API revoke pattern as schema forward.
-- ---------------------------------------------------------------------------

grant select, insert on all tables in schema instruments to research_writer;
grant usage, select on all sequences in schema instruments to research_writer;

alter default privileges in schema instruments
  revoke all on tables from public;

alter default privileges in schema instruments
  grant select, insert on tables to research_writer;

revoke all on all tables in schema instruments from public;
revoke all on all tables in schema instruments from anon;
revoke all on all tables in schema instruments from authenticated;
revoke all on all tables in schema instruments from service_role;

revoke all on all functions in schema instruments from public;
revoke all on all functions in schema instruments from anon;
revoke all on all functions in schema instruments from authenticated;
revoke all on all functions in schema instruments from service_role;

grant execute on all functions in schema instruments to research_writer;

alter default privileges in schema instruments
  revoke execute on functions from public;

alter default privileges in schema instruments
  grant execute on functions to research_writer;
