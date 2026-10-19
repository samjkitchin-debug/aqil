-- Portfolio journal: stable event identity, idempotency and corrections.
-- Unapplied. Do not db push. Does not modify 20261018210000_my_wealth.sql.
-- Order: after 20261020120000.

create table public.wealth_journal_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  account_id uuid not null references public.wealth_accounts (id) on delete cascade,
  event_type text not null,
  occurred_on date not null,
  settled_on date,
  instrument_id uuid references public.wealth_instruments (id),
  quantity numeric(24, 8),
  unit_price_minor bigint,
  cash_amount_minor bigint,
  currency char(3) not null,
  fees_minor bigint not null default 0,
  tax_minor bigint not null default 0,
  fx_rate_id uuid references public.wealth_fx_rates (id),
  source_type text not null,
  source_ref text,
  batch_id uuid references public.wealth_import_batches (id),
  idempotency_key text not null,
  correction_of uuid references public.wealth_journal_events (id),
  transfer_group_id uuid,
  split_numerator integer,
  split_denominator integer,
  created_at timestamptz not null default now(),
  constraint wealth_journal_events_type check (
    event_type in (
      'deposit',
      'withdrawal',
      'transfer',
      'buy',
      'sell',
      'fee',
      'distribution',
      'reinvestment',
      'tax',
      'split',
      'correction'
    )
  ),
  constraint wealth_journal_events_source check (
    source_type in (
      'manual',
      'csv',
      'broker_readonly',
      'system_corporate_action',
      'correction'
    )
  ),
  constraint wealth_journal_events_currency check (currency ~ '^[A-Z]{3}$'),
  constraint wealth_journal_events_idempotency_key check (
    char_length(idempotency_key) between 1 and 200
  ),
  constraint wealth_journal_events_idempotency unique (user_id, idempotency_key),
  constraint wealth_journal_events_not_self check (correction_of is distinct from id),
  constraint wealth_journal_events_fees check (fees_minor >= 0 and tax_minor >= 0),
  constraint wealth_journal_events_unit_price check (
    unit_price_minor is null or unit_price_minor >= 0
  ),
  constraint wealth_journal_events_split_ratio check (
    (
      event_type = 'split'
      and split_numerator > 0
      and split_denominator > 0
    )
    or (
      event_type <> 'split'
      and split_numerator is null
      and split_denominator is null
    )
  ),
  constraint wealth_journal_events_transfer_group check (
    (event_type = 'transfer' and transfer_group_id is not null)
    or (event_type <> 'transfer' and transfer_group_id is null)
  ),
  constraint wealth_journal_events_buy check (
    event_type <> 'buy'
    or (
      instrument_id is not null
      and quantity > 0
      and (cash_amount_minor is null or cash_amount_minor <= 0)
    )
  ),
  constraint wealth_journal_events_sell check (
    event_type <> 'sell'
    or (
      instrument_id is not null
      and quantity < 0
      and (cash_amount_minor is null or cash_amount_minor >= 0)
    )
  ),
  constraint wealth_journal_events_reinvestment check (
    event_type <> 'reinvestment'
    or (
      instrument_id is not null
      and quantity > 0
      and (cash_amount_minor is null or cash_amount_minor <= 0)
    )
  ),
  constraint wealth_journal_events_fee check (
    event_type <> 'fee'
    or (
      quantity is null
      and instrument_id is null
      and cash_amount_minor is not null
      and cash_amount_minor < 0
    )
  ),
  constraint wealth_journal_events_tax check (
    event_type <> 'tax'
    or (
      quantity is null
      and instrument_id is null
      and cash_amount_minor is not null
      and cash_amount_minor < 0
    )
  ),
  constraint wealth_journal_events_distribution check (
    event_type <> 'distribution'
    or (
      quantity is null
      and cash_amount_minor is not null
      and cash_amount_minor > 0
    )
  ),
  constraint wealth_journal_events_deposit check (
    event_type <> 'deposit'
    or (
      quantity is null
      and instrument_id is null
      and cash_amount_minor is not null
      and cash_amount_minor > 0
    )
  ),
  constraint wealth_journal_events_withdrawal check (
    event_type <> 'withdrawal'
    or (
      quantity is null
      and instrument_id is null
      and cash_amount_minor is not null
      and cash_amount_minor < 0
    )
  ),
  constraint wealth_journal_events_transfer check (
    event_type <> 'transfer'
    or (
      (
        quantity is null
        and instrument_id is null
        and cash_amount_minor is not null
        and cash_amount_minor <> 0
      )
      or (
        cash_amount_minor is null
        and instrument_id is not null
        and quantity is not null
        and quantity <> 0
      )
    )
  ),
  constraint wealth_journal_events_split check (
    event_type <> 'split'
    or (
      instrument_id is not null
      and quantity is null
      and cash_amount_minor is null
      and unit_price_minor is null
    )
  ),
  constraint wealth_journal_events_correction check (
    event_type <> 'correction'
    or (
      correction_of is not null
      and quantity is null
      and cash_amount_minor is null
      and unit_price_minor is null
      and instrument_id is null
    )
  )
);

comment on table public.wealth_journal_events is
  'Append-only portfolio journal. A correction inserts a new row; it does not rewrite the original.';

comment on column public.wealth_journal_events.id is
  'Stable event identity. A correction does not replace this value.';

comment on column public.wealth_journal_events.idempotency_key is
  'Unique per owner. Repeating the key is the same event, not a second posting.';

comment on column public.wealth_journal_events.correction_of is
  'Set on the later event. The referenced row stays as it was inserted.';

comment on column public.wealth_journal_events.quantity is
  'Signed units into the account. Buys are positive and sells are negative.';

comment on column public.wealth_journal_events.cash_amount_minor is
  'Signed minor units into the account, already including fees and tax. Null means the cash leg was not observed.';

comment on column public.wealth_journal_events.unit_price_minor is
  'Booked unit price in minor units. Null means no price was observed.';

comment on column public.wealth_journal_events.fx_rate_id is
  'Optional link to an observed rate. A missing rate is not treated as 1.';

create unique index wealth_journal_events_one_correction_idx
  on public.wealth_journal_events (correction_of)
  where correction_of is not null;

create index wealth_journal_events_account_idx
  on public.wealth_journal_events (user_id, account_id, occurred_on);

create index wealth_journal_events_transfer_idx
  on public.wealth_journal_events (user_id, transfer_group_id)
  where transfer_group_id is not null;

create or replace function public.wealth_journal_correction_same_owner()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
declare
  owner uuid;
begin
  if new.correction_of is null then
    return new;
  end if;
  select user_id
    into owner
  from public.wealth_journal_events
  where id = new.correction_of;
  if owner is null or owner <> new.user_id then
    raise exception 'correction_of must reference an event of the same owner'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create trigger wealth_journal_correction_same_owner
before insert on public.wealth_journal_events
for each row
execute function public.wealth_journal_correction_same_owner();

create or replace function public.wealth_journal_reject_update()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  raise exception 'journal events are append-only'
    using errcode = '55000';
end;
$$;

create trigger wealth_journal_reject_update
before update on public.wealth_journal_events
for each row
execute function public.wealth_journal_reject_update();

create or replace function public.wealth_journal_transfer_zero_sum()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  if exists (
    select 1
    from (
      select event.instrument_id, sum(event.quantity) as instrument_sum
      from public.wealth_journal_events event
      where event.user_id = new.user_id
        and event.transfer_group_id = new.transfer_group_id
        and event.event_type = 'transfer'
        and not exists (
          select 1
          from public.wealth_journal_events newer
          where newer.correction_of = event.id
        )
      group by event.instrument_id
    ) sums
    where sums.instrument_id is not null
      and sums.instrument_sum <> 0
  ) then
    raise exception 'transfer group is not zero-sum'
      using errcode = '23514';
  end if;

  if exists (
    select 1
    from (
      select event.currency, sum(event.cash_amount_minor) as cash_sum
      from public.wealth_journal_events event
      where event.user_id = new.user_id
        and event.transfer_group_id = new.transfer_group_id
        and event.event_type = 'transfer'
        and not exists (
          select 1
          from public.wealth_journal_events newer
          where newer.correction_of = event.id
        )
      group by event.currency
    ) sums
    where sums.cash_sum <> 0
  ) then
    raise exception 'transfer group is not zero-sum'
      using errcode = '23514';
  end if;

  return null;
end;
$$;

create constraint trigger wealth_journal_transfer_zero_sum
after insert on public.wealth_journal_events
deferrable initially deferred
for each row
when (new.event_type = 'transfer')
execute function public.wealth_journal_transfer_zero_sum();

alter table public.wealth_journal_events enable row level security;

create policy wealth_journal_select_own on public.wealth_journal_events
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy wealth_journal_insert_own on public.wealth_journal_events
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1
      from public.wealth_accounts account
      where account.id = account_id
        and account.user_id = (select auth.uid())
    )
    and (
      instrument_id is null
      or exists (
        select 1
        from public.wealth_instruments instrument
        where instrument.id = instrument_id
          and instrument.user_id = (select auth.uid())
      )
    )
    and (
      fx_rate_id is null
      or exists (
        select 1
        from public.wealth_fx_rates rate
        where rate.id = fx_rate_id
          and rate.user_id = (select auth.uid())
      )
    )
    and (
      batch_id is null
      or exists (
        select 1
        from public.wealth_import_batches batch
        where batch.id = batch_id
          and batch.user_id = (select auth.uid())
      )
    )
  );

revoke all on table public.wealth_journal_events from public, anon, authenticated, service_role;
grant select, insert on table public.wealth_journal_events to authenticated;
grant select, insert on table public.wealth_journal_events to service_role;

revoke all on function public.wealth_journal_correction_same_owner() from public, anon, authenticated;
revoke all on function public.wealth_journal_reject_update() from public, anon, authenticated;
revoke all on function public.wealth_journal_transfer_zero_sum() from public, anon, authenticated;
grant execute on function public.wealth_journal_correction_same_owner() to authenticated, service_role;
grant execute on function public.wealth_journal_reject_update() to authenticated, service_role;
grant execute on function public.wealth_journal_transfer_zero_sum() to authenticated, service_role;
