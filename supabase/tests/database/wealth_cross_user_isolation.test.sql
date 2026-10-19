-- Cross-user wealth denial and anon denial of the token vault.
-- Synthetic users and a synthetic ciphertext only. No archive is loaded.
begin;

select plan(17);

select tests.create_supabase_user('iso_a', 'iso_a@aqil.test');
select tests.create_supabase_user('iso_b', 'iso_b@aqil.test');

insert into public.saxo_token_vault (user_id, environment, ciphertext)
values (tests.get_supabase_uid('iso_a'), 'simulation', 'v1.bm9uY2U.Y2lwaGVy');

select tests.authenticate_as('iso_a');

insert into public.wealth_accounts (user_id, name, provider, environment, currency)
values (tests.get_supabase_uid('iso_a'), 'Manual', 'manual', 'live', 'SGD');

insert into public.wealth_instruments (user_id, name, asset_class, currency)
values (tests.get_supabase_uid('iso_a'), 'World equity', 'global_equity', 'SGD');

insert into public.wealth_valuations (
  user_id, account_id, instrument_id, quantity, currency, amount_minor, as_of, provenance
)
select
  tests.get_supabase_uid('iso_a'),
  account.id,
  instrument.id,
  10,
  'SGD',
  100000,
  '2026-10-01',
  'manual'
from public.wealth_accounts account
join public.wealth_instruments instrument on instrument.user_id = account.user_id
where account.user_id = tests.get_supabase_uid('iso_a');

insert into public.wealth_financial_events (
  user_id, account_id, event_type, amount_minor, currency, occurred_on
)
select
  tests.get_supabase_uid('iso_a'),
  account.id,
  'deposit',
  100000,
  'SGD',
  '2026-10-01'
from public.wealth_accounts account
where account.user_id = tests.get_supabase_uid('iso_a');

insert into public.wealth_allocation_targets (user_id, asset_class, target_weight_bps)
values (tests.get_supabase_uid('iso_a'), 'global_equity', 10000);

select tests.authenticate_as('iso_b');

select is(
  current_user,
  'authenticated',
  'cross-user assertions run as authenticated'
);

select results_eq(
  $$ select count(*)::int from public.wealth_accounts $$,
  $$ values (0) $$,
  'user b cannot read user a accounts'
);
select results_eq(
  $$ select count(*)::int from public.wealth_instruments $$,
  $$ values (0) $$,
  'user b cannot read user a instruments'
);
select results_eq(
  $$ select count(*)::int from public.wealth_valuations $$,
  $$ values (0) $$,
  'user b cannot read user a valuations'
);
select results_eq(
  $$ select count(*)::int from public.wealth_financial_events $$,
  $$ values (0) $$,
  'user b cannot read user a financial events'
);
select results_eq(
  $$ select count(*)::int from public.wealth_allocation_targets $$,
  $$ values (0) $$,
  'user b cannot read user a allocation targets'
);

select results_eq(
  $$
    with deleted as (
      delete from public.wealth_accounts
      where user_id = tests.get_supabase_uid('iso_a')
      returning 1
    )
    select count(*)::int from deleted
  $$,
  $$ values (0) $$,
  'user b cannot delete user a accounts'
);
select results_eq(
  $$
    with deleted as (
      delete from public.wealth_allocation_targets
      where user_id = tests.get_supabase_uid('iso_a')
      returning 1
    )
    select count(*)::int from deleted
  $$,
  $$ values (0) $$,
  'user b cannot delete user a allocation targets'
);

select throws_ok(
  $$ delete from public.wealth_instruments where user_id = tests.get_supabase_uid('iso_a') $$,
  '42501',
  null,
  'user b cannot delete user a instruments'
);
select throws_ok(
  $$ delete from public.wealth_valuations where user_id = tests.get_supabase_uid('iso_a') $$,
  '42501',
  null,
  'user b cannot delete user a valuations'
);
select throws_ok(
  $$ delete from public.wealth_financial_events where user_id = tests.get_supabase_uid('iso_a') $$,
  '42501',
  null,
  'user b cannot delete user a financial events'
);

select tests.authenticate_as('iso_a');
select results_eq(
  $$ select count(*)::int from public.wealth_accounts $$,
  $$ values (1) $$,
  'owner account remains after the other user delete'
);
select results_eq(
  $$ select count(*)::int from public.wealth_instruments $$,
  $$ values (1) $$,
  'owner instrument remains after the other user delete'
);
select results_eq(
  $$ select count(*)::int from public.wealth_valuations $$,
  $$ values (1) $$,
  'owner valuation remains after the other user delete'
);
select results_eq(
  $$ select count(*)::int from public.wealth_financial_events $$,
  $$ values (1) $$,
  'owner financial event remains after the other user delete'
);
select results_eq(
  $$ select count(*)::int from public.wealth_allocation_targets $$,
  $$ values (1) $$,
  'owner allocation target remains after the other user delete'
);

select tests.clear_authentication();
select throws_ok(
  $$ select ciphertext from public.saxo_token_vault $$,
  '42501',
  null,
  'anon cannot read saxo_token_vault'
);

select * from finish();
rollback;
