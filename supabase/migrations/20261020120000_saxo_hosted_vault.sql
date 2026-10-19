-- Hosted Saxo token vault and append-only source units.
-- Unapplied. Do not db push. Local file vault remains the running store.
-- Order: after 20261018210000.

-- Valuation and event inserts previously checked the account owner but not the instrument owner.
drop policy wealth_valuations_insert_own on public.wealth_valuations;
create policy wealth_valuations_insert_own on public.wealth_valuations
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.wealth_accounts account
      where account.id = account_id
        and account.user_id = (select auth.uid())
    )
    and exists (
      select 1 from public.wealth_instruments instrument
      where instrument.id = instrument_id
        and instrument.user_id = (select auth.uid())
    )
  );

drop policy wealth_events_insert_own on public.wealth_financial_events;
create policy wealth_events_insert_own on public.wealth_financial_events
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.wealth_accounts account
      where account.id = account_id
        and account.user_id = (select auth.uid())
    )
    and (
      related_instrument_id is null
      or exists (
        select 1 from public.wealth_instruments instrument
        where instrument.id = related_instrument_id
          and instrument.user_id = (select auth.uid())
      )
    )
  );

create table public.saxo_token_vault (
  user_id uuid not null references auth.users (id) on delete cascade,
  environment text not null,
  ciphertext text not null,
  generation bigint not null default 1,
  status text not null default 'idle',
  rotated_at timestamptz,
  primary key (user_id, environment),
  constraint saxo_token_vault_environment check (environment in ('live', 'simulation')),
  constraint saxo_token_vault_status check (status in ('idle', 'refreshing')),
  constraint saxo_token_vault_generation check (generation > 0),
  constraint saxo_token_vault_ciphertext check (ciphertext ~ '^v1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$')
);

comment on table public.saxo_token_vault is
  'Service-role only. Ciphertext from the application encryption helper. No authenticated select.';

create table public.saxo_source_units (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  environment text not null,
  kind text not null,
  content_hash text not null,
  ciphertext text not null,
  retrieved_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint saxo_source_units_environment check (environment in ('live', 'simulation')),
  constraint saxo_source_units_kind check (char_length(kind) between 1 and 80),
  constraint saxo_source_units_hash check (content_hash ~ '^[0-9a-f]{64}$'),
  constraint saxo_source_units_ciphertext check (ciphertext ~ '^v1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$'),
  constraint saxo_source_units_identity unique (user_id, environment, kind, content_hash)
);

comment on table public.saxo_source_units is
  'Append-only encrypted source copies. This migration does not load any local archive.';

create index saxo_source_units_owner_idx
  on public.saxo_source_units (user_id, environment, retrieved_at desc);

alter table public.saxo_token_vault enable row level security;
alter table public.saxo_source_units enable row level security;

create policy saxo_source_units_select_own on public.saxo_source_units
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy saxo_source_units_insert_own on public.saxo_source_units
  for insert to authenticated
  with check (user_id = (select auth.uid()));

revoke all on table public.saxo_token_vault from public, anon, authenticated;
revoke all on table public.saxo_source_units from public, anon, authenticated;

grant select, insert, update on table public.saxo_token_vault to service_role;
grant select, insert on table public.saxo_source_units to authenticated;
grant select, insert on table public.saxo_source_units to service_role;
