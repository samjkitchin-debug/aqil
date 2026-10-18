-- Private portfolio. Unapplied until an approved hosted batch.
-- Order: after 20261018200000. Do not apply M5's earlier timestamps after this file is on the host.

create table public.wealth_profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  reporting_currency char(3) not null default 'SGD',
  created_at timestamptz not null default now(),
  constraint wealth_profiles_currency check (reporting_currency ~ '^[A-Z]{3}$')
);

create table public.wealth_accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  provider text not null,
  environment text not null,
  currency char(3) not null,
  source_status text not null default 'manual',
  last_successful_refresh_at timestamptz,
  last_attempted_refresh_at timestamptz,
  created_at timestamptz not null default now(),
  constraint wealth_accounts_name check (char_length(name) between 1 and 120),
  constraint wealth_accounts_provider check (provider in ('manual', 'saxo', 'cash', 'other')),
  constraint wealth_accounts_environment check (environment in ('live', 'simulation')),
  constraint wealth_accounts_currency check (currency ~ '^[A-Z]{3}$'),
  constraint wealth_accounts_source_status check (
    source_status in ('manual', 'current', 'stale', 'source_error', 'incomplete')
  )
);

create index wealth_accounts_user_id_idx on public.wealth_accounts (user_id);

create table public.wealth_instruments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  isin text,
  name text not null,
  asset_class text not null,
  currency char(3) not null,
  created_at timestamptz not null default now(),
  constraint wealth_instruments_name check (char_length(name) between 1 and 200),
  constraint wealth_instruments_currency check (currency ~ '^[A-Z]{3}$'),
  constraint wealth_instruments_class check (
    asset_class in (
      'global_equity',
      'thematic_technology',
      'investment_grade_bonds',
      'cash_investable',
      'emergency_reserve'
    )
  )
);

create unique index wealth_instruments_user_isin_idx
  on public.wealth_instruments (user_id, isin)
  where isin is not null;

create table public.wealth_import_batches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  idempotency_key text not null,
  source_label text not null,
  status text not null,
  error_summary text,
  created_at timestamptz not null default now(),
  constraint wealth_import_batches_status check (status in ('accepted', 'rejected', 'failed')),
  constraint wealth_import_batches_key unique (user_id, idempotency_key)
);

create table public.wealth_valuations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  account_id uuid not null references public.wealth_accounts (id) on delete cascade,
  instrument_id uuid not null references public.wealth_instruments (id) on delete cascade,
  quantity numeric(24, 8) not null,
  currency char(3) not null,
  amount_minor bigint not null,
  as_of date not null,
  provenance text not null,
  import_batch_id uuid references public.wealth_import_batches (id),
  created_at timestamptz not null default now(),
  constraint wealth_valuations_quantity check (quantity >= 0),
  constraint wealth_valuations_amount check (amount_minor >= 0),
  constraint wealth_valuations_currency check (currency ~ '^[A-Z]{3}$'),
  constraint wealth_valuations_provenance check (provenance in ('manual', 'import'))
);

create index wealth_valuations_lookup_idx
  on public.wealth_valuations (user_id, account_id, instrument_id, created_at desc);

comment on table public.wealth_valuations is
  'Append-only valuation observations. A later value does not replace an earlier row.';

create table public.wealth_allocation_targets (
  user_id uuid not null references auth.users (id) on delete cascade,
  asset_class text not null,
  target_weight_bps integer not null,
  primary key (user_id, asset_class),
  constraint wealth_targets_class check (
    asset_class in (
      'global_equity',
      'thematic_technology',
      'investment_grade_bonds',
      'cash_investable'
    )
  ),
  constraint wealth_targets_bps check (target_weight_bps >= 0 and target_weight_bps <= 10000)
);

create table public.wealth_fx_rates (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  base_currency char(3) not null,
  quote_currency char(3) not null,
  rate numeric(20, 10) not null,
  observation_date date not null,
  source text not null,
  retrieved_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint wealth_fx_rate_positive check (rate > 0),
  constraint wealth_fx_pair check (base_currency <> quote_currency),
  constraint wealth_fx_base check (base_currency ~ '^[A-Z]{3}$'),
  constraint wealth_fx_quote check (quote_currency ~ '^[A-Z]{3}$')
);

comment on column public.wealth_fx_rates.rate is
  'Quote currency units for one base currency unit. Never assumed to be 1.';

create table public.wealth_financial_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  account_id uuid not null references public.wealth_accounts (id) on delete cascade,
  event_type text not null,
  amount_minor bigint not null,
  currency char(3) not null,
  related_instrument_id uuid references public.wealth_instruments (id),
  occurred_on date not null,
  note text,
  created_at timestamptz not null default now(),
  constraint wealth_events_type check (
    event_type in (
      'deposit',
      'withdrawal',
      'purchase',
      'sale',
      'distribution',
      'fee',
      'transfer',
      'cash_adjustment',
      'correction'
    )
  ),
  constraint wealth_events_amount check (amount_minor > 0),
  constraint wealth_events_currency check (currency ~ '^[A-Z]{3}$'),
  constraint wealth_events_trade_has_instrument check (
    event_type not in ('purchase', 'sale') or related_instrument_id is not null
  )
);

create or replace function public.wealth_targets_must_total_10000()
returns trigger
language plpgsql
as $$
declare
  total integer;
  owner uuid;
begin
  owner := coalesce(new.user_id, old.user_id);
  select coalesce(sum(target_weight_bps), 0)
    into total
  from public.wealth_allocation_targets
  where user_id = owner;
  if total <> 0 and total <> 10000 then
    raise exception 'allocation targets must total 10000 basis points'
      using errcode = '23514';
  end if;
  return null;
end;
$$;

create constraint trigger wealth_targets_sum
after insert or update or delete on public.wealth_allocation_targets
deferrable initially deferred
for each row
execute function public.wealth_targets_must_total_10000();

alter table public.wealth_profiles enable row level security;
alter table public.wealth_accounts enable row level security;
alter table public.wealth_instruments enable row level security;
alter table public.wealth_import_batches enable row level security;
alter table public.wealth_valuations enable row level security;
alter table public.wealth_allocation_targets enable row level security;
alter table public.wealth_fx_rates enable row level security;
alter table public.wealth_financial_events enable row level security;

create policy wealth_profiles_select_own on public.wealth_profiles
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_profiles_insert_own on public.wealth_profiles
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy wealth_profiles_update_own on public.wealth_profiles
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy wealth_accounts_all_own on public.wealth_accounts
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy wealth_instruments_all_own on public.wealth_instruments
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy wealth_imports_select_own on public.wealth_import_batches
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_imports_insert_own on public.wealth_import_batches
  for insert to authenticated with check (user_id = (select auth.uid()));

create policy wealth_valuations_select_own on public.wealth_valuations
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_valuations_insert_own on public.wealth_valuations
  for insert to authenticated with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.wealth_accounts account
      where account.id = account_id and account.user_id = (select auth.uid())
    )
  );

create policy wealth_targets_all_own on public.wealth_allocation_targets
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy wealth_fx_select_own on public.wealth_fx_rates
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_fx_insert_own on public.wealth_fx_rates
  for insert to authenticated with check (user_id = (select auth.uid()));

create policy wealth_events_select_own on public.wealth_financial_events
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_events_insert_own on public.wealth_financial_events
  for insert to authenticated with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.wealth_accounts account
      where account.id = account_id and account.user_id = (select auth.uid())
    )
  );

revoke all on table public.wealth_profiles from public, anon, authenticated;
revoke all on table public.wealth_accounts from public, anon, authenticated;
revoke all on table public.wealth_instruments from public, anon, authenticated;
revoke all on table public.wealth_import_batches from public, anon, authenticated;
revoke all on table public.wealth_valuations from public, anon, authenticated;
revoke all on table public.wealth_allocation_targets from public, anon, authenticated;
revoke all on table public.wealth_fx_rates from public, anon, authenticated;
revoke all on table public.wealth_financial_events from public, anon, authenticated;

grant select, insert, update on table public.wealth_profiles to authenticated;
grant select, insert, update, delete on table public.wealth_accounts to authenticated;
grant select, insert, update on table public.wealth_instruments to authenticated;
grant select, insert on table public.wealth_import_batches to authenticated;
grant select, insert on table public.wealth_valuations to authenticated;
grant select, insert, update, delete on table public.wealth_allocation_targets to authenticated;
grant select, insert on table public.wealth_fx_rates to authenticated;
grant select, insert on table public.wealth_financial_events to authenticated;

grant all on table public.wealth_profiles to service_role;
grant all on table public.wealth_accounts to service_role;
grant all on table public.wealth_instruments to service_role;
grant all on table public.wealth_import_batches to service_role;
grant all on table public.wealth_valuations to service_role;
grant all on table public.wealth_allocation_targets to service_role;
grant all on table public.wealth_fx_rates to service_role;
grant all on table public.wealth_financial_events to service_role;

revoke all on function public.wealth_targets_must_total_10000() from public, anon, authenticated;
