-- Additive ETF market-data foundation. Do not edit 20261024120000_etf_instruments.sql.
-- Do not apply this file to the preserved database postgres.
-- instruments stays off the Supabase Data API. anon, authenticated, and
-- service_role stay revoked. Writes stay with research_writer. Web reads use
-- etf_reader, which is NOLOGIN until a deploy step sets a password outside Git.

do $$
begin
  create role etf_reader
    nologin
    nosuperuser
    nocreatedb
    nocreaterole
    noinherit;
exception
  when duplicate_object then null;
end $$;

comment on role etf_reader is
  'Read-only ETF access for the server-side web application. No insert. Not a Data API role.';

do $$
begin
  execute format('grant connect on database %I to etf_reader', current_database());
end $$;

grant usage on schema instruments to etf_reader;

-- ---------------------------------------------------------------------------
-- Broker mapping. A Saxo UIC is not a second share class.
-- ---------------------------------------------------------------------------

create table instruments.broker_instruments (
  broker_instrument_id uuid primary key default gen_random_uuid(),
  listing_id uuid not null references instruments.listings (listing_id),
  provider text not null,
  provider_instrument_id text not null,
  asset_type text,
  trading_currency text not null,
  tick_size numeric,
  minimum_trade numeric,
  availability text,
  retrieved_at timestamptz not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint broker_instruments_provider_key unique (provider, provider_instrument_id),
  constraint broker_instruments_provider_present check (length(btrim(provider)) > 0),
  constraint broker_instruments_instrument_present check (
    length(btrim(provider_instrument_id)) > 0
  ),
  constraint broker_instruments_trading_currency check (trading_currency ~ '^[A-Z]{3}$'),
  constraint broker_instruments_tick_non_negative check (
    tick_size is null or tick_size >= 0
  ),
  constraint broker_instruments_minimum_non_negative check (
    minimum_trade is null or minimum_trade >= 0
  )
);

comment on table instruments.broker_instruments is
  'Broker instrument mapped to one listing. Not a share class and not an ISIN.';

-- ---------------------------------------------------------------------------
-- NAV and market prices stay in different tables. Close, bid, ask, last, and
-- adjusted close stay different price types. GBX is stored as GBX.
-- ---------------------------------------------------------------------------

create table instruments.nav_observations (
  nav_observation_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  session_date date not null,
  value numeric not null,
  currency text not null,
  quote_unit text not null,
  price_type text not null default 'nav',
  observation_time timestamptz not null,
  retrieved_at timestamptz not null,
  delay_class text not null,
  adjustment_status text not null,
  adjustment_definition text,
  quality text not null,
  source_id text not null,
  source_locator text not null,
  revision integer not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint nav_observations_price_type check (price_type = 'nav'),
  constraint nav_observations_non_negative check (value >= 0),
  constraint nav_observations_currency check (currency ~ '^[A-Z]{3}$'),
  constraint nav_observations_quote_unit check (quote_unit ~ '^[A-Z]{3}$'),
  constraint nav_observations_delay_class check (
    delay_class in ('realtime', 'delayed', 'end_of_day', 'unknown')
  ),
  constraint nav_observations_adjustment_status check (
    adjustment_status in ('raw', 'adjusted', 'not_applicable')
  ),
  constraint nav_observations_adjusted_definition check (
    adjustment_status <> 'adjusted'
    or (
      adjustment_definition is not null
      and length(btrim(adjustment_definition)) > 0
    )
  ),
  constraint nav_observations_quality check (
    quality in ('accepted', 'stale', 'disagreement', 'rejected')
  ),
  constraint nav_observations_source_present check (
    length(btrim(source_id)) > 0 and length(btrim(source_locator)) > 0
  ),
  constraint nav_observations_revision check (revision >= 1),
  constraint nav_observations_revision_key unique (
    share_class_id, source_id, session_date, revision
  )
);

comment on column instruments.nav_observations.quote_unit is
  'Unit of value. GBX stays GBX and is not divided into GBP in this row.';

comment on table instruments.nav_observations is
  'Share-class NAV. Not a listing close, bid, ask, or last trade.';

create table instruments.market_price_observations (
  market_price_observation_id uuid primary key default gen_random_uuid(),
  listing_id uuid not null references instruments.listings (listing_id),
  session_date date not null,
  value numeric not null,
  currency text not null,
  quote_unit text not null,
  price_type text not null,
  observation_time timestamptz not null,
  retrieved_at timestamptz not null,
  delay_class text not null,
  adjustment_status text not null,
  adjustment_definition text,
  quality text not null,
  source_id text not null,
  source_locator text not null,
  revision integer not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint market_price_observations_price_type check (
    price_type in ('bid', 'ask', 'mid', 'last', 'close', 'adjusted_close')
  ),
  constraint market_price_observations_non_negative check (value >= 0),
  constraint market_price_observations_currency check (currency ~ '^[A-Z]{3}$'),
  constraint market_price_observations_quote_unit check (quote_unit ~ '^[A-Z]{3}$'),
  constraint market_price_observations_delay_class check (
    delay_class in ('realtime', 'delayed', 'end_of_day', 'unknown')
  ),
  constraint market_price_observations_adjustment_status check (
    adjustment_status in ('raw', 'adjusted', 'not_applicable')
  ),
  constraint market_price_observations_adjusted_definition check (
    adjustment_status <> 'adjusted'
    or (
      adjustment_definition is not null
      and length(btrim(adjustment_definition)) > 0
    )
  ),
  constraint market_price_observations_close_is_raw check (
    price_type <> 'close' or adjustment_status = 'raw'
  ),
  constraint market_price_observations_adjusted_close check (
    price_type <> 'adjusted_close' or adjustment_status = 'adjusted'
  ),
  constraint market_price_observations_quality check (
    quality in ('accepted', 'stale', 'disagreement', 'rejected')
  ),
  constraint market_price_observations_source_present check (
    length(btrim(source_id)) > 0 and length(btrim(source_locator)) > 0
  ),
  constraint market_price_observations_revision check (revision >= 1),
  constraint market_price_observations_revision_key unique (
    listing_id, source_id, price_type, session_date, revision
  )
);

comment on table instruments.market_price_observations is
  'Listing prices. Raw close and adjusted close are different rows. A quote is not written over a close.';

comment on column instruments.market_price_observations.quote_unit is
  'Unit of value. GBX stays GBX and is not divided into GBP in this row.';

create index market_price_observations_latest_idx
  on instruments.market_price_observations (
    listing_id, price_type, session_date desc, revision desc
  );

create table instruments.fx_observations (
  fx_observation_id uuid primary key default gen_random_uuid(),
  base_currency text not null,
  quote_currency text not null,
  rate_semantics text not null,
  bid numeric,
  ask numeric,
  mid numeric,
  observation_time timestamptz not null,
  retrieved_at timestamptz not null,
  source_id text not null,
  source_locator text not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint fx_observations_base_currency check (base_currency ~ '^[A-Z]{3}$'),
  constraint fx_observations_quote_currency check (quote_currency ~ '^[A-Z]{3}$'),
  constraint fx_observations_pair_distinct check (base_currency <> quote_currency),
  constraint fx_observations_rate_semantics check (
    rate_semantics in ('reference', 'broker')
  ),
  constraint fx_observations_one_rate check (
    bid is not null or ask is not null or mid is not null
  ),
  constraint fx_observations_non_negative check (
    (bid is null or bid >= 0)
    and (ask is null or ask >= 0)
    and (mid is null or mid >= 0)
  ),
  constraint fx_observations_source_present check (
    length(btrim(source_id)) > 0 and length(btrim(source_locator)) > 0
  )
);

comment on table instruments.fx_observations is
  'Reference FX and broker FX are different rate_semantics. A missing source is not a rate.';

create table instruments.converted_amounts (
  converted_amount_id uuid primary key default gen_random_uuid(),
  amount numeric not null,
  currency text not null,
  quote_unit text not null,
  fx_observation_id uuid not null references instruments.fx_observations (fx_observation_id),
  market_price_observation_id uuid references instruments.market_price_observations (
    market_price_observation_id
  ),
  nav_observation_id uuid references instruments.nav_observations (nav_observation_id),
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint converted_amounts_non_negative check (amount >= 0),
  constraint converted_amounts_currency check (currency ~ '^[A-Z]{3}$'),
  constraint converted_amounts_quote_unit check (quote_unit ~ '^[A-Z]{3}$'),
  constraint converted_amounts_one_parent check (
    num_nonnulls(market_price_observation_id, nav_observation_id) = 1
  )
);

comment on table instruments.converted_amounts is
  'A converted amount keeps the FX observation it used. The raw price row is not rewritten.';

-- ---------------------------------------------------------------------------
-- Eligibility and founder approval are separate append-only decisions.
-- ---------------------------------------------------------------------------

create table instruments.eligibility_decisions (
  eligibility_decision_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  decision text not null,
  conditions text not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint eligibility_decisions_decision check (
    decision in ('eligible', 'insufficient', 'rejected')
  ),
  constraint eligibility_decisions_conditions_present check (length(btrim(conditions)) > 0)
);

comment on table instruments.eligibility_decisions is
  'Append-only eligibility from stated conditions. Not a founder approval and not a score. CORE is not this table.';

create table instruments.approval_decisions (
  approval_decision_id uuid primary key default gen_random_uuid(),
  share_class_id uuid not null references instruments.share_classes (share_class_id),
  decision text not null,
  actor text not null,
  rationale text not null,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint approval_decisions_decision check (
    decision in ('approved', 'restricted', 'suspended', 'rejected', 'retired')
  ),
  constraint approval_decisions_actor_present check (length(btrim(actor)) > 0),
  constraint approval_decisions_rationale_present check (length(btrim(rationale)) > 0)
);

comment on table instruments.approval_decisions is
  'Append-only founder approval. This migration inserts none. Eligibility does not write this table.';

create table instruments.etf_refresh_runs (
  refresh_run_id uuid primary key default gen_random_uuid(),
  dataset text not null,
  provider text not null,
  status text not null,
  idempotency_key text not null,
  error text,
  last_good_observation_at timestamptz,
  started_at timestamptz not null,
  finished_at timestamptz,
  recorded_at timestamptz not null default (timezone('utc', now())),
  constraint etf_refresh_runs_dataset check (
    dataset in ('prices', 'nav', 'holdings', 'fx')
  ),
  constraint etf_refresh_runs_provider_present check (length(btrim(provider)) > 0),
  constraint etf_refresh_runs_status check (
    status in ('running', 'succeeded', 'failed', 'market_closed', 'blocked')
  ),
  constraint etf_refresh_runs_idempotency_key unique (idempotency_key),
  constraint etf_refresh_runs_idempotency_present check (length(btrim(idempotency_key)) > 0),
  constraint etf_refresh_runs_finished_order check (
    finished_at is null or finished_at >= started_at
  )
);

comment on table instruments.etf_refresh_runs is
  'One ETF dataset refresh. A holdings failure does not delete price rows.';

create trigger nav_observations_deny_mutation
before update or delete on instruments.nav_observations
for each row
execute function instruments.deny_row_mutation();

create trigger market_price_observations_deny_mutation
before update or delete on instruments.market_price_observations
for each row
execute function instruments.deny_row_mutation();

create trigger fx_observations_deny_mutation
before update or delete on instruments.fx_observations
for each row
execute function instruments.deny_row_mutation();

create trigger converted_amounts_deny_mutation
before update or delete on instruments.converted_amounts
for each row
execute function instruments.deny_row_mutation();

create trigger eligibility_decisions_deny_mutation
before update or delete on instruments.eligibility_decisions
for each row
execute function instruments.deny_row_mutation();

create trigger approval_decisions_deny_mutation
before update or delete on instruments.approval_decisions
for each row
execute function instruments.deny_row_mutation();

create trigger broker_instruments_deny_mutation
before update or delete on instruments.broker_instruments
for each row
execute function instruments.deny_row_mutation();

create trigger etf_refresh_runs_deny_delete
before delete on instruments.etf_refresh_runs
for each row
execute function instruments.deny_row_mutation();

-- ---------------------------------------------------------------------------
-- Privileges. etf_reader can select the existing instruments tables and these
-- new tables. research_writer can insert. Only refresh runs may be updated.
-- ---------------------------------------------------------------------------

grant select on all tables in schema instruments to etf_reader;

grant select, insert on table instruments.broker_instruments to research_writer;
grant select, insert on table instruments.nav_observations to research_writer;
grant select, insert on table instruments.market_price_observations to research_writer;
grant select, insert on table instruments.fx_observations to research_writer;
grant select, insert on table instruments.converted_amounts to research_writer;
grant select, insert on table instruments.eligibility_decisions to research_writer;
grant select, insert on table instruments.approval_decisions to research_writer;
grant select, insert, update on table instruments.etf_refresh_runs to research_writer;

revoke update, delete, truncate on table instruments.broker_instruments from research_writer;
revoke update, delete, truncate on table instruments.nav_observations from research_writer;
revoke update, delete, truncate on table instruments.market_price_observations from research_writer;
revoke update, delete, truncate on table instruments.fx_observations from research_writer;
revoke update, delete, truncate on table instruments.converted_amounts from research_writer;
revoke update, delete, truncate on table instruments.eligibility_decisions from research_writer;
revoke update, delete, truncate on table instruments.approval_decisions from research_writer;
revoke delete, truncate on table instruments.etf_refresh_runs from research_writer;

revoke all on table instruments.broker_instruments from public, anon, authenticated, service_role;
revoke all on table instruments.nav_observations from public, anon, authenticated, service_role;
revoke all on table instruments.market_price_observations from public, anon, authenticated, service_role;
revoke all on table instruments.fx_observations from public, anon, authenticated, service_role;
revoke all on table instruments.converted_amounts from public, anon, authenticated, service_role;
revoke all on table instruments.eligibility_decisions from public, anon, authenticated, service_role;
revoke all on table instruments.approval_decisions from public, anon, authenticated, service_role;
revoke all on table instruments.etf_refresh_runs from public, anon, authenticated, service_role;

revoke all on schema instruments from anon, authenticated, service_role;

alter default privileges in schema instruments
  grant select on tables to etf_reader;
