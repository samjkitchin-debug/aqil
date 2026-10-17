-- RLS tests for My Wealth tables (synthetic users).
begin;

select plan(3);

select tests.create_supabase_user('wealth_a', 'wealth_a@aqil.test');
select tests.create_supabase_user('wealth_b', 'wealth_b@aqil.test');

select tests.authenticate_as('wealth_a');
insert into public.wealth_profiles (user_id, base_currency, emergency_reserve_minor)
values (tests.get_supabase_uid('wealth_a'), 'SGD', 10000);

insert into public.wealth_positions (
  user_id, name, asset_class, currency, market_value_minor, valuation_date
) values (
  tests.get_supabase_uid('wealth_a'),
  'Fixture ETF',
  'global_equity',
  'SGD',
  50000,
  '2026-10-01'
);

select tests.authenticate_as('wealth_b');
select results_eq(
  $$ select count(*)::int from public.wealth_positions $$,
  $$ values (0) $$,
  'user_b cannot read user_a positions'
);

select throws_ok(
  $$
    insert into public.wealth_positions (
      user_id, name, asset_class, currency, market_value_minor, valuation_date
    ) values (
      tests.get_supabase_uid('wealth_a'),
      'Hostile',
      'global_equity',
      'SGD',
      1,
      '2026-10-01'
    )
  $$,
  '42501',
  null,
  'user_b cannot insert positions for user_a'
);

select tests.clear_authentication();
select throws_ok(
  $$ select * from public.wealth_profiles $$,
  '42501',
  null,
  'anon cannot select wealth_profiles'
);

select * from finish();
rollback;
