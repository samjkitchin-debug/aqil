-- Owner isolation for My Wealth. Synthetic users only.
begin;

select plan(8);

select tests.create_supabase_user('wealth_a', 'wealth_a@aqil.test');
select tests.create_supabase_user('wealth_b', 'wealth_b@aqil.test');

create temp table wealth_ids (account_id uuid, instrument_id uuid);
grant select, insert on wealth_ids to authenticated;

select tests.authenticate_as('wealth_a');
insert into public.wealth_accounts (user_id, name, provider, environment, currency)
values (tests.get_supabase_uid('wealth_a'), 'Manual', 'manual', 'live', 'SGD');

insert into public.wealth_instruments (user_id, name, asset_class, currency, isin)
values (tests.get_supabase_uid('wealth_a'), 'World equity', 'global_equity', 'SGD', 'IE00BTEST000');

insert into public.wealth_valuations (
  user_id, account_id, instrument_id, quantity, currency, amount_minor, as_of, provenance
)
select
  tests.get_supabase_uid('wealth_a'),
  account.id,
  instrument.id,
  10,
  'SGD',
  100000,
  '2026-10-01',
  'manual'
from public.wealth_accounts account
join public.wealth_instruments instrument on instrument.user_id = account.user_id
where account.user_id = tests.get_supabase_uid('wealth_a');

insert into wealth_ids (account_id, instrument_id)
select account.id, instrument.id
from public.wealth_accounts account
join public.wealth_instruments instrument on instrument.user_id = account.user_id
where account.user_id = tests.get_supabase_uid('wealth_a');

select tests.authenticate_as('wealth_b');
select results_eq(
  $$ select count(*)::int from public.wealth_accounts $$,
  $$ values (0) $$,
  'user b cannot read user a accounts'
);
select results_eq(
  $$ select count(*)::int from public.wealth_valuations $$,
  $$ values (0) $$,
  'user b cannot read user a valuations'
);

select throws_ok(
  $$
    insert into public.wealth_valuations (
      user_id, account_id, instrument_id, quantity, currency, amount_minor, as_of, provenance
    )
    select tests.get_supabase_uid('wealth_a'), account_id, instrument_id, 1, 'SGD', 1, '2026-10-02', 'manual'
    from wealth_ids
  $$,
  '42501',
  null,
  'user b cannot insert a valuation on user a account'
);

update public.wealth_accounts set name = 'taken';
select tests.authenticate_as('wealth_a');
select results_eq(
  $$ select name from public.wealth_accounts where environment = 'live' $$,
  $$ values ('Manual'::text) $$,
  'user b cannot rename user a account'
);
select tests.authenticate_as('wealth_a');
select throws_ok(
  $$
    insert into public.wealth_instruments (user_id, name, asset_class, currency)
    values (tests.get_supabase_uid('wealth_a'), 'Unknown', 'global_equity_guess', 'SGD')
  $$,
  '23514',
  null,
  'unknown asset class is rejected'
);

select throws_ok(
  $$
    update public.wealth_valuations
    set amount_minor = 1
    where user_id = tests.get_supabase_uid('wealth_a')
  $$,
  '42501',
  null,
  'valuation history cannot be updated'
);

select tests.clear_authentication();
select throws_ok(
  $$ select * from public.wealth_accounts $$,
  '42501',
  null,
  'anon cannot read accounts'
);

select tests.authenticate_as('wealth_a');
select lives_ok(
  $$
    insert into public.wealth_accounts (user_id, name, provider, environment, currency)
    values (tests.get_supabase_uid('wealth_a'), 'Paper', 'manual', 'simulation', 'USD')
  $$,
  'a simulation account stays a separate row'
);

select * from finish();
rollback;
