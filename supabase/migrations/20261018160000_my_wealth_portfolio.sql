-- G2: private portfolio, allocation targets, contributions (owner-only RLS).

create table public.wealth_profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  base_currency char(3) not null default 'SGD',
  emergency_reserve_minor bigint not null default 0,
  constraint wealth_profiles_currency check (base_currency ~ '^[A-Z]{3}$'),
  constraint wealth_profiles_reserve_nonneg check (emergency_reserve_minor >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.wealth_profiles is
  'Per-user wealth plan metadata. Emergency reserve is excluded from investable allocation maths.';

create table public.wealth_positions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  isin text,
  symbol text,
  name text not null,
  asset_class text not null,
  thematic_label text,
  currency char(3) not null,
  market_value_minor bigint not null,
  valuation_date date not null,
  units numeric(24, 8),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint wealth_positions_currency check (currency ~ '^[A-Z]{3}$'),
  constraint wealth_positions_value_nonneg check (market_value_minor >= 0),
  constraint wealth_positions_name_len check (char_length(name) between 1 and 200)
);

create index wealth_positions_user_id_idx on public.wealth_positions (user_id);

create table public.wealth_allocation_targets (
  user_id uuid not null references auth.users (id) on delete cascade,
  asset_class text not null,
  target_weight_bps integer not null,
  primary key (user_id, asset_class),
  constraint wealth_targets_bps_range check (
    target_weight_bps >= 0 and target_weight_bps <= 10000
  )
);

comment on table public.wealth_allocation_targets is
  'Strategic allocation targets in basis points (10000 = 100%). Not updated by research runs.';

create table public.wealth_contribution_plans (
  user_id uuid primary key references auth.users (id) on delete cascade,
  amount_minor bigint not null,
  currency char(3) not null,
  cadence text not null default 'monthly',
  day_of_month smallint,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint wealth_contribution_plans_currency check (currency ~ '^[A-Z]{3}$'),
  constraint wealth_contribution_plans_amount_pos check (amount_minor > 0),
  constraint wealth_contribution_plans_cadence check (cadence in ('monthly')),
  constraint wealth_contribution_plans_dom check (
    day_of_month is null or (day_of_month >= 1 and day_of_month <= 28)
  )
);

create table public.wealth_contribution_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  occurred_at timestamptz not null default now(),
  amount_minor bigint not null,
  currency char(3) not null,
  note text,
  created_at timestamptz not null default now(),
  constraint wealth_contribution_events_currency check (currency ~ '^[A-Z]{3}$'),
  constraint wealth_contribution_events_amount_pos check (amount_minor > 0)
);

create index wealth_contribution_events_user_id_idx
  on public.wealth_contribution_events (user_id, occurred_at desc);

create trigger wealth_profiles_set_updated_at
before update on public.wealth_profiles
for each row execute function public.set_updated_at();

create trigger wealth_positions_set_updated_at
before update on public.wealth_positions
for each row execute function public.set_updated_at();

create trigger wealth_contribution_plans_set_updated_at
before update on public.wealth_contribution_plans
for each row execute function public.set_updated_at();

alter table public.wealth_profiles enable row level security;
alter table public.wealth_positions enable row level security;
alter table public.wealth_allocation_targets enable row level security;
alter table public.wealth_contribution_plans enable row level security;
alter table public.wealth_contribution_events enable row level security;

-- wealth_profiles
create policy wealth_profiles_select_own on public.wealth_profiles
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_profiles_insert_own on public.wealth_profiles
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy wealth_profiles_update_own on public.wealth_profiles
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy wealth_profiles_delete_own on public.wealth_profiles
  for delete to authenticated using (user_id = (select auth.uid()));

-- wealth_positions
create policy wealth_positions_select_own on public.wealth_positions
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_positions_insert_own on public.wealth_positions
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy wealth_positions_update_own on public.wealth_positions
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy wealth_positions_delete_own on public.wealth_positions
  for delete to authenticated using (user_id = (select auth.uid()));

-- wealth_allocation_targets
create policy wealth_targets_select_own on public.wealth_allocation_targets
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_targets_insert_own on public.wealth_allocation_targets
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy wealth_targets_update_own on public.wealth_allocation_targets
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy wealth_targets_delete_own on public.wealth_allocation_targets
  for delete to authenticated using (user_id = (select auth.uid()));

-- wealth_contribution_plans
create policy wealth_plans_select_own on public.wealth_contribution_plans
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_plans_insert_own on public.wealth_contribution_plans
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy wealth_plans_update_own on public.wealth_contribution_plans
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy wealth_plans_delete_own on public.wealth_contribution_plans
  for delete to authenticated using (user_id = (select auth.uid()));

-- wealth_contribution_events
create policy wealth_events_select_own on public.wealth_contribution_events
  for select to authenticated using (user_id = (select auth.uid()));
create policy wealth_events_insert_own on public.wealth_contribution_events
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy wealth_events_update_own on public.wealth_contribution_events
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy wealth_events_delete_own on public.wealth_contribution_events
  for delete to authenticated using (user_id = (select auth.uid()));

revoke all on table public.wealth_profiles from public, anon;
revoke all on table public.wealth_positions from public, anon;
revoke all on table public.wealth_allocation_targets from public, anon;
revoke all on table public.wealth_contribution_plans from public, anon;
revoke all on table public.wealth_contribution_events from public, anon;

grant select, insert, update, delete on table public.wealth_profiles to authenticated;
grant select, insert, update, delete on table public.wealth_positions to authenticated;
grant select, insert, update, delete on table public.wealth_allocation_targets to authenticated;
grant select, insert, update, delete on table public.wealth_contribution_plans to authenticated;
grant select, insert, update, delete on table public.wealth_contribution_events to authenticated;

grant all on table public.wealth_profiles to service_role;
grant all on table public.wealth_positions to service_role;
grant all on table public.wealth_allocation_targets to service_role;
grant all on table public.wealth_contribution_plans to service_role;
grant all on table public.wealth_contribution_events to service_role;
